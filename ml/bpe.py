"""Byte-level BPE tokenizer implemented from scratch.

Starts from the 256 raw bytes and greedily learns the most frequent adjacent
pair merges. This is the same family of algorithm used by GPT-2/GPT-4, written
here with no external tokenizer dependency.

Reference behaviour:
    * ``train`` counts pairs over pre-tokenized words and records merges.
    * ``encode`` re-applies the learned merges by rank.
    * ``decode`` maps ids back to bytes and decodes UTF-8.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

# GPT-2-ish pre-tokenization without requiring the ``regex`` module.
PAT = re.compile(r"'(?:[sdmt]|ll|ve|re)| ?[^\W\d_]+| ?\d+| ?[^\s\w]+|\s+")

BOS = "<bos>"
EOS = "<eos>"
SPECIAL_TOKENS = (BOS, EOS)


def _get_pairs(ids: list[int]) -> set[tuple[int, int]]:
    return set(zip(ids, ids[1:]))


def _merge(ids: list[int], pair: tuple[int, int], new_id: int) -> list[int]:
    out: list[int] = []
    i = 0
    n = len(ids)
    while i < n:
        if i < n - 1 and ids[i] == pair[0] and ids[i + 1] == pair[1]:
            out.append(new_id)
            i += 2
        else:
            out.append(ids[i])
            i += 1
    return out


class BPETokenizer:
    def __init__(self, merges: dict[tuple[int, int], int], specials: dict[str, int]):
        self.merges = {tuple(k): int(v) for k, v in merges.items()}
        self.specials = dict(specials)
        self.ranks = {pair: i for i, pair in enumerate(self.merges)}
        # Precompute the byte string for every learned merge id.
        self.id_to_bytes: dict[int, bytes] = {i: bytes([i]) for i in range(256)}
        for (a, b), new_id in self.merges.items():
            self.id_to_bytes[new_id] = self.id_to_bytes[a] + self.id_to_bytes[b]

    # ------------------------------------------------------------------ train
    @classmethod
    def train(
        cls,
        text: str,
        vocab_size: int = 1024,
        max_merges: int | None = None,
    ) -> "BPETokenizer":
        num_merges = (max_merges if max_merges is not None else vocab_size - 256 - len(SPECIAL_TOKENS))
        num_merges = max(0, num_merges)

        word_freqs = Counter(PAT.findall(text))
        words = {tuple(int(b) for b in w.encode("utf-8")): c for w, c in word_freqs.items()}

        merges: dict[tuple[int, int], int] = {}
        for i in range(num_merges):
            pairs: Counter = Counter()
            for word, freq in words.items():
                for pair in _get_pairs(list(word)):
                    pairs[pair] += freq
            if not pairs:
                break
            best = max(pairs, key=pairs.get)
            if pairs[best] < 2:
                break
            new_id = 256 + i
            merges[best] = new_id
            words = {tuple(_merge(list(word), best, new_id)): freq for word, freq in words.items()}

        specials = {tok: 256 + len(merges) + j for j, tok in enumerate(SPECIAL_TOKENS)}
        return cls(merges, specials)

    # ----------------------------------------------------------------- encode
    def _encode_word(self, word: str) -> list[int]:
        ids = list(word.encode("utf-8"))
        while len(ids) >= 2:
            pairs = _get_pairs(ids)
            best = min(pairs, key=lambda p: self.ranks.get(p, float("inf")))
            if best not in self.ranks:
                break
            ids = _merge(ids, best, self.merges[best])
        return ids

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> list[int]:
        ids: list[int] = []
        for word in PAT.findall(text):
            ids.extend(self._encode_word(word))
        if add_bos:
            ids.insert(0, self.specials[BOS])
        if add_eos:
            ids.append(self.specials[EOS])
        return ids

    # ----------------------------------------------------------------- decode
    def decode(self, ids, skip_special: bool = True) -> str:
        spec = set(self.specials.values()) if skip_special else set()
        out = bytearray()
        for i in ids:
            i = int(i)
            if i in spec:
                continue
            chunk = self.id_to_bytes.get(i)
            if chunk is not None:
                out.extend(chunk)
        return out.decode("utf-8", errors="replace")

    @property
    def vocab_size(self) -> int:
        return 256 + len(self.merges) + len(self.specials)

    @property
    def bos_id(self) -> int:
        return self.specials[BOS]

    @property
    def eos_id(self) -> int:
        return self.specials[EOS]

    # ------------------------------------------------------------- persistence
    def save(self, path: str | Path) -> None:
        payload = {
            "merges": [[list(k), v] for k, v in self.merges.items()],
            "specials": self.specials,
        }
        Path(path).write_text(json.dumps(payload), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "BPETokenizer":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        merges = {(int(a), int(b)): int(v) for (a, b), v in payload["merges"]}
        return cls(merges, {k: int(v) for k, v in payload["specials"].items()})
