#!/usr/bin/env python3
"""Layout memory: stops every cover from having the same shape. Colour is ignored (a brand palette is fixed anyway).

  python layout_memory.py check <cover.png> [--memory .atelier/covers]   # compare with the last 8 remembered covers
  python layout_memory.py add <cover.png> --name <id> [--memory .atelier/covers]   # remember a delivered cover

Without --memory it uses the covers of the nearest .atelier folder at or above the current folder, as compose.py finds it, so a
check run from a page's own folder sees the project's covers (in the 30 Oct 2026 run it said "PASS against 0" from there).

Each cover becomes a 32x40 edge map (where the shapes are). Pearson correlation above 0.55 with a recent cover
FAILS (move the main mass, change the grid); above 0.45 warns. Idea from huashu-design's layout record (MIT).
Pillow only. Exit 1 on FAIL.
"""
import argparse
import pathlib
import shutil
import sys

from PIL import Image, ImageFilter

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None


def vec(png):
    img = Image.open(png).convert("L").resize((128, 160)).filter(ImageFilter.FIND_EDGES).resize((32, 40), Image.BOX)
    return list(img.tobytes())


def corr(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((y - mb) ** 2 for y in b) ** 0.5
    return cov / (va * vb) if va and vb else 0.0


def nearest_covers():
    """.atelier/covers of the nearest .atelier at or above the current folder; with none, ./.atelier/covers."""
    here = pathlib.Path.cwd().resolve()
    return next((d / ".atelier" / "covers" for d in (here, *here.parents) if (d / ".atelier").is_dir()), here / ".atelier" / "covers")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "add"])
    ap.add_argument("cover")
    ap.add_argument("--memory", help="the covers folder; default: .atelier/covers of the nearest .atelier at or above this folder")
    ap.add_argument("--name")
    ap.add_argument("--last", type=int, default=8)
    a = ap.parse_args()
    mem = pathlib.Path(a.memory) if a.memory else nearest_covers()
    if a.cmd == "add":   # only add makes the folder: a check that made one would leave a stray .atelier where compose.py then finds an empty project
        mem.mkdir(parents=True, exist_ok=True)
        name = a.name or pathlib.Path(a.cover).parent.name
        shutil.copy(a.cover, mem / f"{name}.png")
        print(f"remembered {name} in {mem}")
        return 0
    v = vec(a.cover)
    past = sorted(mem.glob("*.png"), key=lambda p: p.stat().st_mtime)[-a.last:]
    fails = 0
    for p in past:
        c = corr(v, vec(p))
        if c > 0.55:
            print(f"  FAIL {c:.2f} alike with {p.stem}: move the main mass, change the grid or the ground")
            fails += 1
        elif c > 0.45:
            print(f"  warn {c:.2f} alike with {p.stem}")
    print(f"layout memory: {'FAIL' if fails else 'PASS'} against {len(past)} remembered cover(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
