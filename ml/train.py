"""Train the from-scratch transformer language model.

Examples:
    python -m ml.train --preset small --steps 3000
    python -m ml.train --data ml/data/tinyshakespeare.txt --tokenizer bpe --vocab-size 1024
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import sys
import time
from pathlib import Path

import torch

from .bpe import BPETokenizer
from .config import GPTConfig, PRESETS, apply_preset
from .dataset import default_data_path, split_ids
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
    from .dataset import get_batch

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


def save_checkpoint(out_dir: Path, model, config, tokenizer, kind, metrics, args) -> None:
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


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Train a small GPT from scratch.")
    parser.add_argument("--data", nargs="+", default=None)
    parser.add_argument("--out", default="ml/runs/run")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="small")
    parser.add_argument("--tokenizer", choices=["bpe", "char"], default="bpe")
    parser.add_argument("--vocab-size", type=int, default=1024, help="BPE target vocab")
    parser.add_argument("--max-chars", type=int, default=1_000_000,
                        help="cap corpus characters used for training")
    parser.add_argument("--steps", type=int, default=3000)
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
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    device = pick_device(args.device)
    out_dir = Path(args.out)

    data_paths = args.data or [default_data_path()]
    text = load_text(data_paths)
    if args.max_chars and len(text) > args.max_chars:
        text = text[: args.max_chars]

    tokenizer = build_tokenizer(args.tokenizer, text, args.vocab_size)
    cache_dir = Path(__file__).resolve().parent / "data" / ".cache"
    ids = encode_with_cache(text, tokenizer, args.tokenizer, cache_dir)
    train_data, val_data = split_ids(ids, val_frac=0.1)
    splits = {"train": train_data, "val": val_data}

    config = apply_preset(GPTConfig(vocab_size=tokenizer.vocab_size), args.preset)
    config.block_size = min(config.block_size, max(2, len(train_data) - 1))

    model = GPT(config).to(device)
    print(f"device={device} preset={args.preset} tokenizer={args.tokenizer} "
          f"vocab={tokenizer.vocab_size} params={model.num_params():,} tokens={len(ids):,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    best_val = float("inf")
    t0 = time.time()

    for step in range(args.steps):
        lr = lr_at(step, args.steps, args.warmup, args.lr, args.min_lr)
        for group in optimizer.param_groups:
            group["lr"] = lr

        from .dataset import get_batch

        batch = get_batch(train_data, config.block_size, args.batch_size, device)
        _, loss = model(batch.x, batch.y)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        if step % args.eval_interval == 0 or step == args.steps - 1:
            metrics = estimate_loss(model, splits, config, args.batch_size, device, args.eval_iters)
            print(f"step {step:5d} | train {metrics['train']:.3f} | "
                  f"val {metrics['val']:.3f} | lr {lr:.2e} | {time.time() - t0:.0f}s")
            if metrics["val"] <= best_val:
                best_val = metrics["val"]
                save_checkpoint(out_dir, model, config, tokenizer, args.tokenizer, metrics, args)

    start = torch.tensor([tokenizer.encode(args.sample_prompt, add_bos=True)], device=device)
    out_ids = model.generate(start, max_new_tokens=args.sample_tokens, temperature=0.8, top_k=40)
    print("\nsample:\n" + tokenizer.decode(out_ids[0].tolist()))


if __name__ == "__main__":
    main()
