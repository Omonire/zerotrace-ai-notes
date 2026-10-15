"""Configuration for the from-scratch transformer language model."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class GPTConfig:
    vocab_size: int = 256
    block_size: int = 128      # maximum context length (tokens)
    n_layer: int = 4           # number of transformer blocks
    n_head: int = 4            # number of attention heads
    n_embd: int = 128          # embedding / residual width
    dropout: float = 0.1
    bias: bool = True          # use bias in Linear/LayerNorm layers

    def to_dict(self) -> dict:
        return asdict(self)


TINY = dict(block_size=64, n_layer=2, n_head=2, n_embd=64, dropout=0.0)
MINI = dict(block_size=128, n_layer=3, n_head=4, n_embd=96, dropout=0.1)
SMALL = dict(block_size=128, n_layer=4, n_head=4, n_embd=128, dropout=0.1)
MEDIUM = dict(block_size=256, n_layer=6, n_head=6, n_embd=384, dropout=0.1)

PRESETS = {"tiny": TINY, "mini": MINI, "small": SMALL, "medium": MEDIUM}


def apply_preset(config: GPTConfig, name: str) -> GPTConfig:
    if name not in PRESETS:
        raise ValueError(f"Unknown preset '{name}'. Choose from {sorted(PRESETS)}")
    for key, value in PRESETS[name].items():
        setattr(config, key, value)
    return config
