"""Generate text with a trained from-scratch transformer.

Example:
    python -m ml.generate --run ml/runs/run --prompt "ROMEO: " --tokens 200
"""

from __future__ import annotations

import argparse
import sys

import torch

from .backend import LocalLM


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Sample text from a trained GPT.")
    parser.add_argument("--run", default="ml/runs/run", help="run directory with ckpt.pt")
    parser.add_argument("--prompt", default="ROMEO: ")
    parser.add_argument("--tokens", type=int, default=200)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=40)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--device", default=None)
    parser.add_argument("--count", type=int, default=1, help="number of samples")
    args = parser.parse_args()

    if args.seed is not None:
        torch.manual_seed(args.seed)

    lm = LocalLM.from_run(args.run, args.device)
    for i in range(args.count):
        text = lm.generate(
            args.prompt,
            max_new_tokens=args.tokens,
            temperature=args.temperature,
            top_k=args.top_k or None,
            top_p=args.top_p if args.top_p < 1.0 else None,
        )
        print(f"--- sample {i + 1} ---")
        print(text)
        print()


if __name__ == "__main__":
    main()
