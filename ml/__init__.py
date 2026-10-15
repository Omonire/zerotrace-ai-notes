"""From-scratch transformer language model for AI Notes.

This package is import-safe without PyTorch installed: heavy modules are
resolved lazily via ``__getattr__`` so the web app can probe availability
(e.g. ``from ml import backend; backend.is_available()``) on any interpreter.

Modules:
    tokenizer  char-level tokenizer
    bpe        byte-level BPE tokenizer (from scratch)
    config     model hyper-parameters and presets
    model      the GPT-style decoder-only transformer
    dataset    corpus loading and batching
    train      training entry point (``python -m ml.train``)
    generate   sampling entry point (``python -m ml.generate``)
    backend    local inference for the web app
"""

from __future__ import annotations

__all__ = ["GPT", "GPTConfig", "CharTokenizer", "BPETokenizer"]


def __getattr__(name: str):
    if name == "GPT":
        from .model import GPT

        return GPT
    if name == "GPTConfig":
        from .config import GPTConfig

        return GPTConfig
    if name == "CharTokenizer":
        from .tokenizer import CharTokenizer

        return CharTokenizer
    if name == "BPETokenizer":
        from .bpe import BPETokenizer

        return BPETokenizer
    raise AttributeError(f"module 'ml' has no attribute '{name}'")
