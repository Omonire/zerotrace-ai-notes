"""Local inference backend for the from-scratch transformer.

Loads a trained checkpoint + tokenizer and exposes simple ``generate`` and
``chat`` helpers. Torch is imported lazily so the web app can import this
module even when torch (or a trained model) is unavailable.
"""

from __future__ import annotations

import threading
from pathlib import Path

RUN_ENV_VAR = "LOCAL_MODEL_PATH"
DEFAULT_RUN = "ml/runs/run"

_lock = threading.Lock()
_cache: dict[str, "LocalLM"] = {}


def _tokenizer_from(run_dir: Path, kind: str):
    if kind == "char":
        from .tokenizer import CharTokenizer

        return CharTokenizer.load(run_dir / "tokenizer.json")
    from .bpe import BPETokenizer

    return BPETokenizer.load(run_dir / "tokenizer.json")


def _load_ckpt(path: Path, device: str, attempts: int = 3):
    """Load a checkpoint, tolerating a concurrent writer replacing the file."""
    import time

    import torch

    last_exc = None
    for _ in range(attempts):
        try:
            return torch.load(path, map_location=device, weights_only=False)
        except Exception as exc:  # transient read during an in-progress save
            last_exc = exc
            time.sleep(0.5)
    raise last_exc


class LocalLM:
    def __init__(self, model, tokenizer, device: str, run_dir: Path):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.run_dir = run_dir

    @classmethod
    def from_run(cls, run: str | Path, device: str | None = None) -> "LocalLM":
        import torch

        from .config import GPTConfig
        from .model import GPT

        run_dir = Path(run)
        ckpt_path = run_dir / "ckpt.pt"
        if not ckpt_path.exists():
            raise FileNotFoundError(f"no checkpoint at {ckpt_path}")

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        ckpt = _load_ckpt(ckpt_path, device)
        tokenizer = _tokenizer_from(run_dir, ckpt.get("tokenizer_type", "char"))
        config = GPTConfig(**ckpt["config"])
        model = GPT(config).to(device)
        model.load_state_dict(ckpt["model_state"])
        model.eval()
        return cls(model, tokenizer, device, run_dir)

    def generate(self, prompt: str, max_new_tokens: int = 200, temperature: float = 0.8,
                 top_k: int | None = 40, top_p: float | None = None) -> str:
        import torch

        ids = self.tokenizer.encode(prompt, add_bos=True)
        idx = torch.tensor([ids], device=self.device)
        out = self.model.generate(
            idx, max_new_tokens=max_new_tokens,
            temperature=temperature, top_k=top_k, top_p=top_p,
        )
        return self.tokenizer.decode(out[0].tolist())

    def chat(self, messages: list[dict], notes_context: str = "", max_new_tokens: int = 220) -> str:
        """Render a small chat transcript and continue it."""
        lines = []
        if notes_context:
            lines.append("Notes:\n" + notes_context.strip())
        for msg in messages:
            role = msg.get("role", "user")
            speaker = "User" if role == "user" else "Assistant"
            lines.append(f"{speaker}: {msg.get('content', '').strip()}")
        lines.append("Assistant:")
        prompt = "\n".join(lines)
        text = self.generate(prompt, max_new_tokens=max_new_tokens)
        # Keep only the model's continuation after the final "Assistant:".
        marker = "Assistant:"
        if marker in text:
            text = text.rsplit(marker, 1)[-1]
        stop = text.find("\nUser:")
        if stop != -1:
            text = text[:stop]
        return text.strip()


def get_local_model(run: str | Path | None = None, device: str | None = None) -> "LocalLM":
    """Load (and cache) a local model. Raises if torch/model are unavailable."""
    import os

    run = run or os.environ.get(RUN_ENV_VAR, DEFAULT_RUN)
    key = f"{Path(run).resolve()}::{device}"
    with _lock:
        if key not in _cache:
            _cache[key] = LocalLM.from_run(run, device)
        return _cache[key]


def is_available(run: str | Path | None = None) -> bool:
    """True if torch is importable and a checkpoint exists for ``run``."""
    import os

    run = run or os.environ.get(RUN_ENV_VAR, DEFAULT_RUN)
    run_dir = Path(run)
    if not (run_dir / "ckpt.pt").exists():
        return False
    try:
        import torch  # noqa: F401
    except Exception:
        return False
    return True
