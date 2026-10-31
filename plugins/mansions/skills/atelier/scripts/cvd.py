#!/usr/bin/env python3
"""See a design the way about 1 in 12 men see it: colour-vision deficiency simulation, plus an accent check.

  python cvd.py <folder or page.png>

Writes <name>.cvd.png next to each page: the original and the protan, deutan and tritan simulations side by side
(Machado, Oliveira and Fernandes 2009 matrices, full severity, applied in linear RGB).
If boxes.json from `render.mjs --audit` is present, the accent, number and hook boxes are compared with the page
ground in every simulation: if an element only stands out by hue (its luminance contrast with the ground is under
1.6:1 while it looked distinct in colour), it WARNs: add a lightness difference, a shape or a label.
The last line is the verdict: "cvd: PASS" or "cvd: WARN <n> pages: <reason>". A warning is advice: exit 0 either way.
Exit 2 if the folder has no page-NN.png. Pillow only.
"""
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageStat

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

PAGES = "page-[0-9][0-9].png"  # two digits only, so the page-NN.cvd.png strips written here are never read back

M = {
    "protan": (0.152286, 1.052583, -0.204868, 0.114503, 0.786281, 0.099216, -0.003882, -0.048116, 1.051998),
    "deutan": (0.367322, 0.860646, -0.227968, 0.280085, 0.672501, 0.047413, -0.011820, 0.042940, 0.968881),
    "tritan": (1.255528, -0.076749, -0.178779, -0.078411, 0.930809, 0.147602, 0.004733, 0.691367, 0.303900),
}
TO_LIN = [round(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4) * 4095) for v in range(256)]


def from_lin(x):
    x = max(0.0, min(1.0, x / 4095))
    return round(255 * (12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055))


FROM_LIN = [from_lin(i) for i in range(4096)]


def simulate(img, m):
    rgb = img.convert("RGB")
    out = Image.new("RGB", rgb.size)
    src = rgb.tobytes()
    buf = bytearray(len(src))
    for i in range(0, len(src), 3):
        r, g, b = TO_LIN[src[i]], TO_LIN[src[i + 1]], TO_LIN[src[i + 2]]
        buf[i] = FROM_LIN[max(0, min(4095, int(m[0] * r + m[1] * g + m[2] * b)))]
        buf[i + 1] = FROM_LIN[max(0, min(4095, int(m[3] * r + m[4] * g + m[5] * b)))]
        buf[i + 2] = FROM_LIN[max(0, min(4095, int(m[6] * r + m[7] * g + m[8] * b)))]
    out.frombytes(bytes(buf))
    return out


def lum(c):
    lin = [((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4) for v in c]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a, b):
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def dist(a, b):
    return sum((p - q) ** 2 for p, q in zip(a, b)) ** 0.5


def check(png, boxes):
    img = Image.open(png).convert("RGB")
    small = img.resize((img.width // 3, img.height // 3))
    sims = {k: simulate(small, m) for k, m in M.items()}
    sheet = Image.new("RGB", (small.width * 4 + 30, small.height + 40), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate([("original", small)] + list(sims.items())):
        sheet.paste(im, (6 + i * (small.width + 6), 34))
        draw.text((8 + i * (small.width + 6), 10), name, fill=(230, 230, 230))
    out = png.with_name(png.stem + ".cvd.png")
    sheet.save(out)
    warns = []
    ground = tuple(int(v) for v in ImageStat.Stat(small).median)
    for b in boxes:
        if b["role"] not in {"accent", "number", "hook"}:
            continue
        box = tuple(round(v / 3) for v in (b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]))
        if box[2] - box[0] < 2 or box[3] - box[1] < 2:
            continue
        orig = tuple(int(v) for v in ImageStat.Stat(small.crop(box)).mean)
        for name, im in sims.items():
            c = tuple(int(v) for v in ImageStat.Stat(im.crop(box)).mean)
            g = tuple(int(v) for v in ImageStat.Stat(im).median)
            if dist(orig, ground) > 60 and ratio(c, g) < 1.6 and dist(c, g) < 45:
                warns.append(f"{b['role']} blends into the ground for {name} vision (contrast {ratio(c, g):.2f}:1)")
    return out, warns


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    t = pathlib.Path(argv[1])
    pngs = [t] if t.suffix == ".png" else sorted(t.glob(PAGES)) + sorted(t.glob("poster.png"))
    folder = t.parent if t.suffix == ".png" else t
    if not pngs or not all(p.is_file() for p in pngs):
        print(f"no page-NN.png in {folder}: run render.mjs first")
        return 2
    bx = {}
    if (folder / "boxes.json").exists():
        bx = {str(p["page"]).zfill(2): p["boxes"] for p in json.loads((folder / "boxes.json").read_text(encoding="utf-8"))}
    flagged, roles = 0, set()
    for png in pngs:
        out, warns = check(png, bx.get(png.stem.split("-")[-1], []))
        print(f"== {png.name}: {out.name} (original, protan, deutan, tritan)")
        for w in warns:
            print("  warn", w)
        flagged += bool(warns)
        roles.update(w.split(" blends")[0] for w in warns)
    if flagged:
        print(f"cvd: WARN {flagged} pages: {'/'.join(sorted(roles))} blends into the ground for some vision types; add a lightness difference, a shape or a label")
    else:
        print("cvd: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
