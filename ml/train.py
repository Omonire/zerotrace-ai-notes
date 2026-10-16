"""Train the from-scratch transformer language model.

One-shot:
    python -m ml.train --preset small --steps 3000

Continuous / 24-7 (restart-safe; e.g. a Render worker):
    python -m ml.train --resume --continuous --preset small --out /var/data/model

``--resume`` loads ``<out>/ckpt.pt`` if present and keeps training, so the
process can be restarted (deploys, crashes, disk reboots) without losing
progress. ``--continuous`` loops training cycles forever and saves checkpoints
as it goes; SIGINT/SIGTERM triggers a clean checkpoint save before exit.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import signal
import sys
import time
from pathlib import Path

import torch

from .bpe import BPETokenizer
from .config import GPTConfig, PRESETS, apply_preset
from .dataset import default_data_path, get_batch, split_ids
from .model import GPT
from .tokenizer import CharTokenizer


def pick_device(requested: str) -> str:
    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def lr_at(step: int, max_steps: int, warmup: int, lr: float, min_lr: float) -> float:
    if step < warmup:
        return lr * (step + 1) / max(1, warmup)
    if step > max_steps:
        return min_lr
    ratio = (step - warmup) / max(1, max_steps - warmup)
    return min_lr + 0.5 * (1.0 + math.cos(math.pi * ratio)) * (lr - min_lr)


def load_text(paths: list[str]) -> str:
    parts = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(f"corpus file not found: {path}")
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def build_tokenizer(kind: str, text: str, vocab_size: int):
    if kind == "char":
        return CharTokenizer.train(text)
    # Train BPE on a representative slice so vocabulary learning stays fast.
    sample = text if len(text) <= 300_000 else text[:300_000]
    return BPETokenizer.train(sample, vocab_size=vocab_size)


def load_tokenizer(run_dir: Path, kind: str):
    if kind == "char":
        return CharTokenizer.load(run_dir / "tokenizer.json")
    return BPETokenizer.load(run_dir / "tokenizer.json")


def encode_with_cache(text: str, tokenizer, kind: str, cache_dir: Path) -> list[int]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(f"{kind}:{len(text)}:{text[:2000]}".encode("utf-8")).hexdigest()[:12]
    cache_file = cache_dir / f"ids_{kind}_{tokenizer.vocab_size}_{key}.pt"
    if cache_file.exists():
        return torch.load(cache_file, weights_only=False)

    ids: list[int] = []
    for doc in text.split("\n"):
        if doc.strip():
            ids.extend(tokenizer.encode(doc, add_bos=True, add_eos=True))
    torch.save(ids, cache_file)
    return ids


@torch.no_grad()
def estimate_loss(model: GPT, splits, config, batch_size, device, iters):
    model.eval()
    out = {}
    for name, data in splits.items():
        losses = torch.zeros(iters)
        for i in range(iters):
            batch = get_batch(data, config.block_size, batch_size, device)
            _, loss = model(batch.x, batch.y)
            losses[i] = loss.item()
        out[name] = losses.mean().item()
    model.train()
    return out


def save_checkpoint(out_dir: Path, model, config, tokenizer, kind, metrics) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    tokenizer.save(out_dir / "tokenizer.json")
    tmp = out_dir / "ckpt.pt.tmp"
    torch.save(
        {
            "model_state": model.state_dict(),
            "config": config.to_dict(),
            "tokenizer_type": kind,
            "metrics": metrics,
        },
        tmp,
    )
    os.replace(tmp, out_dir / "ckpt.pt")


def load_checkpoint(run_dir: Path, device: str):
    ckpt = torch.load(run_dir / "ckpt.pt", map_location=device, weights_only=False)
    kind = ckpt.get("tokenizer_type", "char")
    tokenizer = load_tokenizer(run_dir, kind)
    config = GPTConfig(**ckpt["config"])
    model = GPT(config).to(device)
    model.load_state_dict(ckpt["model_state"])
    return model, tokenizer, config, kind, ckpt.get("metrics", {})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a small GPT from scratch.")
    parser.add_argument("--data", nargs="+", default=None)
    parser.add_argument("--out", default=os.environ.get("LOCAL_RUN_DIR", "ml/runs/run"))
    parser.add_argument("--preset", choices=sorted(PRESETS), default="small")
    parser.add_argument("--tokenizer", choices=["bpe", "char"], default="bpe")
    parser.add_argument("--vocab-size", type=int, default=1024, help="BPE target vocab")
    parser.add_argument("--max-chars", type=int, default=1_000_000,
                        help="cap corpus characters used for training")
    parser.add_argument("--steps", type=int, default=3000, help="steps per training cycle")
    parser.add_argument("--batch-size", type=int, default=48)
    parser.add_argument("--lr", type=float, default=6e-4)
    parser.add_argument("--min-lr", type=float, default=6e-5)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--eval-interval", type=int, default=250)
    parser.add_argument("--eval-iters", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--sample-prompt", default="ROMEO: ")
    parser.add_argument("--sample-tokens", type=int, default=200)
    parser.add_argument("--resume", action="store_true",
                        help="continue from <out>/ckpt.pt if it exists")
    parser.add_argument("--init-from", default=None,
                        help="resume from a specific run directory instead of --out")
    parser.add_argument("--continuous", action="store_true",
                        help="loop training cycles forever (24/7 worker)")
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

    args = parse_args()
    torch.manual_seed(args.seed)
    device = pick_device(args.device)
    out_dir = Path(args.out)
    cache_dir = Path(__file__).resolve().parent / "data" / ".cache"

    text = load_text(args.data or [default_data_path()])
    if args.max_chars and len(text) > args.max_chars:
        text = text[: args.max_chars]

    resume_dir = Path(args.init_from) if args.init_from else out_dir
    can_resume = (args.resume or args.init_from) and (resume_dir / "ckpt.pt").exists()

    if can_resume:
        model, tokenizer, config, kind, metrics = load_checkpoint(resume_dir, device)
        print(f"resumed from {resume_dir / 'ckpt.pt'} | params={model.num_params():,}", flush=True)
    else:
        tokenizer = build_tokenizer(args.tokenizer, text, args.vocab_size)
        kind = args.tokenizer
        config = apply_preset(GPTConfig(vocab_size=tokenizer.vocab_size), args.preset)
        model = GPT(config).to(device)
        metrics = {}

    ids = encode_with_cache(text, tokenizer, kind, cache_dir)
    train_data, val_data = split_ids(ids, val_frac=0.1)
    splits = {"train": train_data, "val": val_data}
    config.block_size = min(config.block_size, max(2, len(train_data) - 1))
    model.to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    best_val = metrics.get("val", float("inf"))
    last_metrics = metrics or {"train": float("nan"), "val": float("nan")}

    print(f"device={device} preset={args.preset} tokenizer={kind} "
          f"vocab={tokenizer.vocab_size} params={model.num_params():,} tokens={len(ids):,} "
          f"continuous={args.continuous}", flush=True)

    stop = {"flag": False}

    def _handle(signum, _frame):
        stop["flag"] = True
        print(f"\nreceived signal {signum}; will checkpoint and exit.", flush=True)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle)
        except (ValueError, OSError):
            pass

    cycle = 0
    while True:
        cycle += 1
        if args.continuous:
            print(f"=== cycle {cycle} ===", flush=True)
        t0 = time.time()

        for step in range(args.steps):
            lr = lr_at(step, args.steps, args.warmup, args.lr, args.min_lr)
            for group in optimizer.param_groups:
                group["lr"] = lr

            batch = get_batch(train_data, config.block_size, args.batch_size, device)
            _, loss = model(batch.x, batch.y)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            if stop["flag"]:
                save_checkpoint(out_dir, model, config, tokenizer, kind, last_metrics)
                print("checkpoint saved on shutdown.", flush=True)
                return

            if step % args.eval_interval == 0 or step == args.steps - 1:
                last_metrics = estimate_loss(
                    model, splits, config, args.batch_size, device, args.eval_iters
                )
                print(f"cycle {cycle} step {step:5d} | train {last_metrics['train']:.3f} | "
                      f"val {last_metrics['val']:.3f} | lr {lr:.2e} | {time.time() - t0:.0f}s",
                      flush=True)
                # Continuous training always persists the latest state.
                if args.continuous or last_metrics["val"] <= best_val:
                    save_checkpoint(out_dir, model, config, tokenizer, kind, last_metrics)
                    best_val = min(best_val, last_metrics["val"])

        if args.sample_tokens > 0:
            start = torch.tensor([tokenizer.encode(args.sample_prompt, add_bos=True)], device=device)
            out_ids = model.generate(start, max_new_tokens=args.sample_tokens, temperature=0.8, top_k=40)
            print(f"\ncycle {cycle} sample:\n" + tokenizer.decode(out_ids[0].tolist()) + "\n", flush=True)

        if not args.continuous:
            break


if __name__ == "__main__":
    main()
