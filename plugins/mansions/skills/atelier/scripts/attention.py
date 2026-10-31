#!/usr/bin/env python3
"""Where does the eye land first? A bottom-up saliency map for a rendered page.

  python attention.py posts/<date>/<id>            # every page-NN.png (and poster.png) in the folder
  python attention.py posts/<date>/<id>/page-01.png

Model: a simplified Itti, Koch and Niebur (1998) saliency model. Intensity and two colour-opponent
channels (red-green, blue-yellow), centre-surround differences at three scales, each map weighted so that
maps with a few strong peaks count more than maps with many weak ones, then summed and blurred.
It predicts which shapes and colours pop out in the first glance, before reading starts. It underrates text
(people fixate text whatever its contrast, Cerf, Frady and Koch 2009), so reading order is checked separately:
render.mjs --audit fails a cover whose hook or number is not the biggest type. A rough guide, not truth.

If boxes.json exists (written by `node render.mjs <visual.html> --audit`; for a film's poster.png, the boxes at the poster time that
`--audit --seconds N --poster T` adds, else page 1's), each element with a
data-role (hook, number, object, accent, body, logo, fine) gets a share: the part of the page's total predicted
attention that falls inside its box. A bigger salient region holds more, so a 9px line cannot beat a 540px numeral
and a smaller logo scores lower. The shares give the rank, which is the predicted looking order. A mild centre
bias is applied (Judd et al. 2009). An accent inside a hook or number box counts as that element (its pixels are
already in that share). Rules:
  cover (page 1): the hook, the number or the object must win.
    The logo must never win (FAIL). An accent or other labelled element may not beat the best hook, number or
    object by more than 1.5x (FAIL; a closer lead is a note, because a saliency model underrates text). An object
    (a drawing or picture) may lead, because any saliency model rates a picture above type; render.mjs --audit
    checks that the hook is the biggest type. Body and fine print take no part in this race (their share is still
    printed): a block of body type would win by area, and labelling less must not be rewarded.
  any page: an element with no data-role must never hold the strongest spot. The global peak must not sit
    outside every data-role box with more than 1.5x the saliency of the strongest part of any labelled box (FAIL).
  any page: a logo whose ink is under 3:1 against the ground around it fails (a lockup made for the other ground).
Writes attention-NN.png heat overlays next to the input. Pillow only.
A page with boxes.json and no data-role at all fails: nothing says what should lead it. Exit 1 on a FAIL, 2 if the folder has no page-NN.png.
"""
import json
import pathlib
import sys

from PIL import Image, ImageChops, ImageFilter, ImageMath, ImageOps, ImageStat

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

W = 270  # working width (1080 / 4)
PAGES = "page-[0-9][0-9].png"  # two digits only: cvd.py writes page-NN.cvd.png next to the pages
COVER_OK = {"hook", "number", "object"}  # roles that may lead the cover
NO_LEAD = {"body", "fine"}  # type to be read: its share is printed, but it never takes part in the cover race
MARGIN = 1.5  # how far another labelled element may lead the best hook, number or object before the cover fails


def channels(img):
    rgb = img.convert("RGB").resize((W, round(img.height * W / img.width)), Image.LANCZOS)
    r, g, b = rgb.split()
    inten = rgb.convert("L")
    # opponent channels, offset to stay in 0..255
    rg = ImageChops.subtract(r, g, scale=2.0, offset=128)
    yellow = ImageChops.add(r, g, scale=2.0)
    by = ImageChops.subtract(b, yellow, scale=2.0, offset=128)
    return rgb, [inten, rg, by]


def norm(m):
    """Scale to 0..255 and weight by (max - mean)^2: few strong peaks beat many weak ones (Itti's N operator)."""
    ext = m.getextrema()[1] or 1
    m = m.point(lambda v: v * 255 / ext)
    mean = ImageStat.Stat(m).mean[0]
    w = ((255 - mean) / 255) ** 2
    return m.point(lambda v: v * w)


def add(a, b):
    return ImageMath.lambda_eval(lambda e: e["a"] + e["b"], a=a.convert("F"), b=b.convert("F"))


def saliency(img):
    rgb, chans = channels(img)
    acc = Image.new("F", rgb.size, 0)
    for ch in chans:
        cmaps = Image.new("F", rgb.size, 0)
        for c in (1, 2, 4):
            centre = ch.filter(ImageFilter.GaussianBlur(c))
            surround = ch.filter(ImageFilter.GaussianBlur(c * 4))
            cmaps = add(cmaps, norm(ImageChops.difference(centre, surround)))
        acc = add(acc, norm(_tol(cmaps)))
    return rgb, centre_bias(_tol(acc).filter(ImageFilter.GaussianBlur(5)))


def _tol(f):
    ext = f.getextrema()[1] or 1
    return f.point(lambda v: v * 255 / ext).convert("L")


def crop_box(sal, box, scale):
    x, y, w, h = (round(v / scale) for v in (box["x"], box["y"], box["w"], box["h"]))
    return sal.crop((max(0, x), max(0, y), min(sal.width, x + w), min(sal.height, y + h)))


def share(sal, box, scale):
    """Percent of the page's total saliency that falls inside the box. It grows with the size of the salient region:
    a thin line scores low and a big numeral high. A 95th percentile rated a 9px line above a 540px numeral."""
    crop = crop_box(sal, box, scale)
    if crop.width < 1 or crop.height < 1:
        return 0.0
    return 100 * ImageStat.Stat(crop).sum[0] / (ImageStat.Stat(sal).sum[0] or 1)


def strongest(sal, box, scale):
    """95th percentile of saliency inside the box: its strongest part. Used only to compare with the global peak."""
    crop = crop_box(sal, box, scale)
    if crop.width < 1 or crop.height < 1:
        return 0.0
    hist = crop.histogram()
    target, seen = 0.95 * sum(hist), 0
    for v, n in enumerate(hist):
        seen += n
        if seen >= target:
            return float(v)
    return 255.0


def centre_bias(sal):
    """People look at the middle of a frame first (Judd et al. 2009). A wide Gaussian lowers corners by about a third."""
    w, h = sal.size
    g = Image.radial_gradient("L").resize((w, h))  # 0 at the centre, 255 at the edge
    g = g.point(lambda v: 255 - int(0.35 * v))
    return ImageChops.multiply(sal, g)


def _pixels(im):
    return getattr(im, "get_flattened_data", im.getdata)()


def _lum(c):
    f = [(v / 255) / 12.92 if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in c[:3]]
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]


def logo_contrast(full, b):
    """Contrast between the logo's ink and the ground around it. A logo made for the other ground vanishes,
    and text checks do not see it because a logo is an image. Non-text marks need 3:1 (WCAG 1.4.11)."""
    x0, y0, x1, y1 = max(b["x"], 0), max(b["y"], 0), min(b["x"] + b["w"], full.width), min(b["y"] + b["h"], full.height)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    m = 10
    ring = [full.crop(r) for r in ((max(x0 - m, 0), y0, x0, y1), (x1, y0, min(x1 + m, full.width), y1),
                                   (x0, max(y0 - m, 0), x1, y0), (x0, y1, x1, min(y1 + m, full.height))) if r[2] > r[0] and r[3] > r[1]]
    if not ring:
        return None
    px = [c for im in ring for c in _pixels(im)]
    ground = tuple(sorted(c[i] for c in px)[len(px) // 2] for i in range(3))
    inside = list(_pixels(full.crop((x0, y0, x1, y1))))
    inside.sort(key=lambda c: -sum(abs(c[i] - ground[i]) for i in range(3)))
    ink = inside[: max(1, len(inside) // 10)]
    ink = tuple(sorted(c[i] for c in ink)[len(ink) // 2] for i in range(3))
    a, g = _lum(ink), _lum(ground)
    return (max(a, g) + 0.05) / (min(a, g) + 0.05)


def part_of(a, b):
    """True when at least half of box a lies inside box b."""
    ix = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    iy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return ix > 0 and iy > 0 and ix * iy >= 0.5 * a["w"] * a["h"]


def analyse(png, boxes):
    img = Image.open(png)
    rgb, sal = saliency(img)
    scale = img.width / W
    heat = ImageOps.colorize(sal, black="#0D0E10", white="#FFF6E8", mid="#206B6F")
    over = Image.blend(rgb, heat.convert("RGB"), 0.6).resize(img.size, Image.LANCZOS)
    idx = png.stem.split("-")[-1]
    out = png.with_name(f"attention-{idx}.png")
    over.save(out)
    # global peak
    px = sal.load()
    peak = max(((px[x, y], x, y) for y in range(sal.height) for x in range(sal.width)))
    fails, notes = [], []
    full = img.convert("RGB")
    for b in boxes or []:   # boxes is None when there is no boxes.json
        if b["role"] == "logo":
            cr = logo_contrast(full, b)
            if cr is not None and cr < 3:
                fails.append(f"the logo nearly disappears on this ground ({cr:.1f}:1; marks need 3:1): use the lockup made for this ground")
            elif cr is not None:
                notes.append(f"logo contrast {cr:.1f}:1")
    if boxes:
        parents = [b for b in boxes if b["role"] in ("hook", "number")]
        held = [b for b in boxes if b["role"] == "accent" and any(part_of(b, p) for p in parents)]
        if held:
            notes.append(f"{len(held)} accent(s) inside a hook or number count as that element")
        ranked = sorted(((share(sal, b, scale), b["role"]) for b in boxes if b not in held), reverse=True)
        notes.append("predicted order (share of the page's attention): " + " > ".join(f"{r} {v:.1f}%" for v, r in ranked))
        inside = any(b["x"] <= peak[1] * scale <= b["x"] + b["w"] and b["y"] <= peak[2] * scale <= b["y"] + b["h"] for b in boxes)
        best = max((strongest(sal, b, scale) for b in boxes if b["role"] != "fine"), default=0)
        if not inside and peak[0] > 1.5 * max(best, 1):
            fails.append(f"the strongest spot ({round(peak[1] * scale)},{round(peak[2] * scale)}) is decoration, not a labelled element: "
                         "an element with no data-role must never hold the strongest spot; label it or tone it down")
        if idx in {"01", "poster"}:
            race = [(v, r) for v, r in ranked if r not in NO_LEAD]
            if not any(r in COVER_OK for _, r in race):
                fails.append('cover: no data-role="hook", "number" or "object" to lead the page: label it')
            else:
                top, win = race[0]
                lead = max(v for v, r in race if r in COVER_OK)
                notes.append(f"cover rule: the hook, the number or the object must win; winner is {win} ({top:.1f}%, best hook, number or object {lead:.1f}%)")
                if win == "logo":
                    fails.append("cover: the logo wins; the hook, the number or the object must win: make the logo smaller or quieter")
                elif win not in COVER_OK and top > MARGIN * max(lead, 0.1):
                    fails.append(f"cover: the {win} wins by more than {MARGIN}x; the hook, the number or the object must win: "
                                 "tone it down, or nest it in the hook or number element so it counts as part of it")
                elif win not in COVER_OK:
                    notes.append(f"the {win} leads the hook, number or object by {top / max(lead, 0.1):.1f}x (under {MARGIN}x passes): check it carries the hook's idea, or tone it down")
    elif boxes is not None:   # the audit wrote boxes.json and found no labelled element: nothing says what should lead the page
        fails.append('no data-role on this page: mark the hook, the number or the object with data-role (and the logo), then run render.mjs --audit again')
    else:
        notes.append('no boxes.json: run render.mjs --audit first, so the labelled elements (data-role) can be checked')
    notes.append(f"peak at ({round(peak[1] * scale)},{round(peak[2] * scale)}); overlay {out.name}")
    return fails, notes


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2 if len(argv) < 2 else 0
    target = pathlib.Path(argv[1])
    pngs = [target] if target.suffix == ".png" else sorted(target.glob(PAGES)) + sorted(target.glob("poster.png"))
    folder = target.parent if target.suffix == ".png" else target
    if not pngs or not all(p.is_file() for p in pngs):
        print(f"no page-NN.png in {folder}: run render.mjs first")
        return 2
    bx = {}
    if (folder / "boxes.json").exists():
        bx = {str(p["page"]).zfill(2): p["boxes"] for p in json.loads((folder / "boxes.json").read_text(encoding="utf-8"))}
    rc = 0
    for png in pngs:
        idx = png.stem.split("-")[-1]
        key = idx if idx != "poster" or "poster" in bx else "01"   # a film's poster: its own boxes when the audit wrote them
        fails, notes = analyse(png, bx.get(key, []) if (folder / "boxes.json").exists() else None)
        print(f"== {png.name}")
        for n in notes:
            print("  ", n)
        for f in fails:
            print("  FAIL", f)
        rc |= bool(fails)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
