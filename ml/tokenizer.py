"""Character-level tokenizer built from scratch.

A minimal, dependency-light tokenizer that maps every unique character in a
corpus to an integer id. It is intentionally simple: the goal is a transparent
building block for the language model, not a production subword tokenizer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

UNK = "<unk>"
BOS = "<bos>"
EOS = "<eos>"
PAD = "<pad>"

SPECIAL_TOKENS = (UNK, BOS, EOS, PAD)


class CharTokenizer:
    """Bidirectional map between characters and integer ids."""

    def __init__(self, stoi: dict[str, int]):
        self.stoi = dict(stoi)
        self.itos = {i: s for s, i in self.stoi.items()}

    @classmethod
    def train(cls, text: str, min_freq: int = 1) -> "CharTokenizer":
        counts: dict[str, int] = {}
        for ch in text:
            counts[ch] = counts.get(ch, 0) + 1

        chars = sorted(ch for ch, c in counts.items() if c >= min_freq)
        stoi = {tok: i for i, tok in enumerate(SPECIAL_TOKENS)}
        for ch in chars:
            if ch not in stoi:
                stoi[ch] = len(stoi)
        return cls(stoi)

    @property
    def vocab_size(self) -> int:
        return len(self.stoi)

    @property
    def unk_id(self) -> int:
        return self.stoi[UNK]

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> list[int]:
        ids = [self.stoi.get(ch, self.unk_id) for ch in text]
        if add_bos:
            ids.insert(0, self.stoi[BOS])
        if add_eos:
            ids.append(self.stoi[EOS])
        return ids

    def decode(self, ids: Iterable[int], skip_special: bool = True) -> str:
        special = set(SPECIAL_TOKENS)
        out = []
        for i in ids:
            ch = self.itos.get(int(i), UNK)
            if skip_special and ch in special:
                continue
            out.append(ch)
        return "".join(out)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.stoi, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "CharTokenizer":
        stoi = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls({str(k): int(v) for k, v in stoi.items()})
