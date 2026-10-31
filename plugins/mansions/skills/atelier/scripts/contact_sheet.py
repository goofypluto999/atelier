#!/usr/bin/env python3
"""Contact sheets: see a whole carousel, or a set of covers, at a glance (critics look at this, not the code).

  python contact_sheet.py <folder>                  # page-NN.png in the folder -> <folder>/preview.png
  python contact_sheet.py <folder> --out <file>     # write the sheet there, not into the folder it reads
  python contact_sheet.py <folder> --pattern "*.png" --cols 4 --labels --out sheet.png

Without --out the sheet overwrites <folder>/preview.png: use --out on a folder you keep under version control.
Only page-NN.png (two digits) is read by default, and cvd.py's page-NN.cvd.png strips are always skipped.
"""
import argparse
import pathlib
import sys

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--pattern", default="page-[0-9][0-9].png", help="files to read (default: page-NN.png)")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--labels", action="store_true")
    ap.add_argument("--out", help="file to write (default: <folder>/preview.png, which overwrites that file)")
    ap.add_argument("--w", type=int, default=360)
    a = ap.parse_args()
    d = pathlib.Path(a.folder)
    paths = sorted(p for p in d.glob(a.pattern) if not p.name.startswith(("preview", "attention-", "sheet")) and ".cvd" not in p.name)
    if not paths:
        print(f"no files matching {a.pattern} in {d}")
        return 1
    first = Image.open(paths[0])
    w = a.w
    h = round(first.height * w / first.width)
    cols = max(1, min(a.cols, len(paths)))
    rows = (len(paths) + cols - 1) // cols
    lab = 30 if a.labels else 0
    sheet = Image.new("RGB", (cols * w + (cols + 1) * 12, rows * (h + lab) + (rows + 1) * 12), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    for i, p in enumerate(paths):
        x, y = 12 + (i % cols) * (w + 12), 12 + (i // cols) * (h + lab + 12)
        im = Image.open(p).convert("RGB")
        scale = min(w / im.width, h / im.height)  # fit inside the cell, keep the aspect ratio
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
        sheet.paste(im, (x + (w - im.width) // 2, y + (h - im.height) // 2))
        if a.labels:
            draw.text((x, y + h + 8), p.stem, fill=(225, 225, 225))
    out = pathlib.Path(a.out) if a.out else d / "preview.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
