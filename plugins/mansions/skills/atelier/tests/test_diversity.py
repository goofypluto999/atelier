#!/usr/bin/env python3
"""Diversity at scale: deliver N pieces and measure what the composer did. python tests/test_diversity.py [N]"""
import json
import math
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_composer import full_piece, own_project  # noqa: E402

TOPICS = ["invoice approvals", "client onboarding", "weekly reporting", "data quality", "handoffs between teams", "tool spend",
          "meeting notes", "support tickets", "hiring pipeline", "forecasting demand", "contract renewals", "inventory counts"]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    with own_project("diversity") as cwd:   # its own project, as test_composer's guard requires: the N pieces fill this memory only
        (cwd / "notes").mkdir()
        genomes = []
        for i in range(n):
            p = full_piece(cwd, f"p{i}", f"{TOPICS[i % len(TOPICS)]} piece {i // len(TOPICS)}", cwd / "notes")
            genomes.append(p["genome"])
        axes = ["format", "direction", "register", "hook", "close", "harmony", "arc", "type"]
        worst = min(sum(1 for a in axes if g[a] != h[a]) for i, g in enumerate(genomes) for h in genomes[max(0, i - 10):i]) if n > 1 else 0
        print(f"{n} pieces delivered; the closest pair within any window of 10 still differs on {worst} of {len(axes)} axes")
        for a in axes:
            vals = [g[a] for g in genomes]
            c = {v: vals.count(v) for v in set(vals)}
            ent = -sum(x / n * math.log2(x / n) for x in c.values())
            print(f"  {a:9} {len(c):3} distinct values, entropy {ent:.2f} bits, max share {max(c.values()) / n:.0%}")
        cov = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve().parent.parent / "scripts" / "compose.py"), "coverage"], cwd=cwd, capture_output=True, text=True).stdout
        print(cov.splitlines()[0])
        assert worst >= 3, "diversity rule broken"
    return 0


if __name__ == "__main__":
    sys.exit(main())
