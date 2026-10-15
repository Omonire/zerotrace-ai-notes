"""Data loading and batching for the language model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch

from .tokenizer import CharTokenizer


@dataclass
class Batch:
    x: torch.Tensor
    y: torch.Tensor


def load_corpus(paths: list[str | Path]) -> str:
    """Read and concatenate one or more text files into a single corpus."""
    parts = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(f"corpus file not found: {path}")
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def split_ids(ids: list[int], val_frac: float = 0.1) -> tuple[torch.Tensor, torch.Tensor]:
    data = torch.tensor(ids, dtype=torch.long)
    n = len(data)
    n_val = max(1, int(n * val_frac)) if n > 1 else 0
    return data[:-n_val] if n_val else data, data[-n_val:] if n_val else data[:0]


def encode_corpus(text: str, tokenizer: CharTokenizer) -> list[int]:
    # Separate documents with <bos>/<eos> so the model learns boundaries.
    ids: list[int] = []
    for doc in text.split("\n"):
        if not doc.strip():
            continue
        ids.extend(tokenizer.encode(doc, add_bos=True, add_eos=True))
    return ids


def default_data_path() -> Path:
    data_dir = Path(__file__).resolve().parent / "data"
    shakespeare = data_dir / "tinyshakespeare.txt"
    return shakespeare if shakespeare.exists() else data_dir / "sample.txt"


def get_batch(
    data: torch.Tensor,
    block_size: int,
    batch_size: int,
    device: str = "cpu",
) -> Batch:
    """Sample a random batch of (input, next-token target) pairs."""
    if len(data) < block_size + 1:
        raise ValueError(
            f"corpus too small: need at least {block_size + 1} tokens, got {len(data)}"
        )
    ix = torch.randint(len(data) - block_size - 1, (batch_size,))
    x = torch.stack([data[i : i + block_size] for i in ix])
    y = torch.stack([data[i + 1 : i + block_size + 1] for i in ix])
    return Batch(x.to(device), y.to(device))
