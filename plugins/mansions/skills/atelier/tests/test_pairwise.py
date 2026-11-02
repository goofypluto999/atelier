#!/usr/bin/env python3
"""Tests for scripts/pairwise.py (1.4.0): two renders compared in both orders. python tests/test_pairwise.py

1. prepare writes order-1.png and order-2.png with the two images swapped, and key.json with their hashes.
2. judge: both critics prefer the same image (1 in order 1, 2 in order 2): a winner, exit 0.
3. judge: both critics prefer position 1, so the preference followed the order: no winner, exit 1.
4. judge refuses (exit 2) a verdict whose "because:" lines neither quote the page nor name a place, and one with no
   "prefer:" line. Needs Pillow."""
import json
import pathlib
import subprocess
import sys
import tempfile

SKILL = pathlib.Path(__file__).resolve().parent.parent
PAIR = SKILL / "scripts" / "pairwise.py"
problems = []


def expect(cond, msg):
    print(("ok    " if cond else "FAIL  ") + msg)
    if not cond:
        problems.append(msg)


def run(*args):
    r = subprocess.run([sys.executable, str(PAIR), *map(str, args)], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout


def verdict(path, prefer, reasons):
    path.write_text("".join([f"prefer: {prefer}\n"] if prefer else []) + "".join(f"because: {r}\n" for r in reasons), encoding="utf-8")
    return path


def main():
    try:
        from PIL import Image
    except ImportError:
        print("SKIP  Pillow not found")
        return 0
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        Image.new("RGB", (108, 135), (200, 30, 30)).save(tmp / "a.png")
        Image.new("RGB", (108, 135), (30, 30, 200)).save(tmp / "b.png")
        code, out = run("prepare", tmp / "a.png", tmp / "b.png", "--out", tmp / "pair")
        key = json.loads((tmp / "pair" / "key.json").read_text(encoding="utf-8"))
        o1, o2 = Image.open(tmp / "pair" / "order-1.png").convert("RGB"), Image.open(tmp / "pair" / "order-2.png").convert("RGB")
        left = (100, o1.height // 2)
        expect(code == 0 and o1.getpixel(left)[0] > 150 and o2.getpixel(left)[2] > 150 and key["order-2"]["1"] == "b"
               and len(key["a"]["sha256"]) == 64, "1. prepare swaps the two images between the sheets and keys them")
        good = ['the hook "Seven of twelve" reads first, top left', "the number on the right holds the page's one accent"]
        code, out = run("judge", tmp / "pair", verdict(tmp / "v1.md", 1, good), verdict(tmp / "v2.md", 2, good))
        expect(code == 0 and "winner a" in out, f"2. the same image preferred in both orders wins (exit {code})")
        code, out = run("judge", tmp / "pair", verdict(tmp / "v1.md", 1, good), verdict(tmp / "v2.md", 1, good))
        expect(code == 1 and "no winner" in out, f"3. a preference that follows the position gives no winner (exit {code})")
        vague = ["it feels more modern", "the colours are nicer overall"]
        code, out = run("judge", tmp / "pair", verdict(tmp / "v1.md", 1, vague), verdict(tmp / "v2.md", 2, good))
        expect(code == 2 and "REFUSED" in out, f"4. reasons with no quote and no place are refused (exit {code})")
        code, out = run("judge", tmp / "pair", verdict(tmp / "v1.md", None, good), verdict(tmp / "v2.md", 2, good))
        expect(code == 2 and "prefer" in out, f"4. a verdict with no prefer line is refused (exit {code})")
    print("PASS" if not problems else f"FAIL {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
