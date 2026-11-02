#!/usr/bin/env python3
"""Compare two renders in both orders, so a critic's preference for whatever it sees first cannot pick the winner.
LLM judges favour the first option shown (references/science.md, "AI reviewers"); a preference counts here only if it
survives the swap. Use it after a revision: is the new attempt better than the best earlier one?

  python pairwise.py prepare <a.png> <b.png> --out <dir>
      writes <dir>/order-1.png (a left, b right) and <dir>/order-2.png (b left, a right), each labelled 1 and 2,
      and <dir>/key.json (which side is which, with each image's sha256). Give each sheet to a FRESH critic
      (art-director) with the same question and the post text; never show it key.json.
  python pairwise.py judge <dir> <verdict-order-1.md> <verdict-order-2.md>
      reads one "prefer: 1" or "prefer: 2" line from each verdict, and its "because:" lines: at least two, each
      quoting the page ("...") or naming a place (left, right, top, bottom, centre, corner, page, line, frame, a
      timestamp). Exit 0 with the winner when both orders prefer the same image; exit 1 when the preference followed
      the position (no winner: keep the earlier attempt); exit 2 when a verdict is missing its lines or its evidence.
"""
import hashlib
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

PLACE = re.compile(r"\b(left|right|top|bottom|centre|center|corner|edge|page \d+|slide \d+|line \d+|row \d+|frame \d+|"
                   r"upper|lower|middle|\d+(\.\d+)? ?s\b)", re.I)
QUOTE = re.compile(r"[\"“][^\"”]{3,}[\"”]")


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def sheet(left, right, out):
    from PIL import Image, ImageDraw, ImageFont
    a, b = Image.open(left).convert("RGB"), Image.open(right).convert("RGB")
    h = 900
    a = a.resize((round(a.width * h / a.height), h))
    b = b.resize((round(b.width * h / b.height), h))
    pad, band = 40, 110
    canvas = Image.new("RGB", (a.width + b.width + 3 * pad, h + band + pad), (40, 42, 46))
    canvas.paste(a, (pad, band))
    canvas.paste(b, (2 * pad + a.width, band))
    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.load_default(size=64)
    except TypeError:   # Pillow before 10.1
        font = ImageFont.load_default()
    d.text((pad, 22), "1", fill=(243, 244, 246), font=font)
    d.text((2 * pad + a.width, 22), "2", fill=(243, 244, 246), font=font)
    canvas.save(out)


def prepare(a, b, out):
    out.mkdir(parents=True, exist_ok=True)
    sheet(a, b, out / "order-1.png")
    sheet(b, a, out / "order-2.png")
    key = {"a": {"file": pathlib.Path(a).name, "sha256": sha(a)}, "b": {"file": pathlib.Path(b).name, "sha256": sha(b)},
           "order-1": {"1": "a", "2": "b"}, "order-2": {"1": "b", "2": "a"}}
    (out / "key.json").write_text(json.dumps(key, indent=1) + "\n", encoding="utf-8")
    print(f"pairwise: {out.name}/order-1.png and order-2.png written; give each to a fresh critic, then run judge")
    return 0


def read_verdict(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    pref = re.findall(r"^\s*prefer:\s*([12])\s*$", text, re.M | re.I)
    because = [l.split(":", 1)[1].strip() for l in text.splitlines() if l.strip().lower().startswith("because:")]
    problems = []
    if len(pref) != 1:
        problems.append(f"{pathlib.Path(path).name}: needs exactly one line \"prefer: 1\" or \"prefer: 2\" (found {len(pref)})")
    located = [b for b in because if QUOTE.search(b) or PLACE.search(b)]
    if len(located) < 2:
        problems.append(f"{pathlib.Path(path).name}: needs 2 or more \"because:\" lines that quote the page or name a place "
                        f"({len(located)} of {len(because)} do)")
    for b in because:
        if b not in located:
            print(f"   not counted (no quote, no place): because: {b[:80]}")
    return (pref[0] if pref else None), problems


def judge(folder, v1, v2):
    key = json.loads((folder / "key.json").read_text(encoding="utf-8"))
    p1, e1 = read_verdict(v1)
    p2, e2 = read_verdict(v2)
    if e1 or e2:
        for e in e1 + e2:
            print("  REFUSED", e)
        return 2
    w1, w2 = key["order-1"][p1], key["order-2"][p2]
    print(f"   order 1 prefers {w1} ({key[w1]['file']}); order 2 prefers {w2} ({key[w2]['file']})")
    if w1 == w2:
        print(f"pairwise: winner {w1} ({key[w1]['file']}), preferred in both orders")
        return 0
    print("pairwise: no winner: each critic preferred the image in the same position, so the order chose, not the work. "
          "Keep the earlier attempt.")
    return 1


def main(argv):
    if len(argv) >= 5 and argv[1] == "prepare" and "--out" in argv:
        return prepare(argv[2], argv[3], pathlib.Path(argv[argv.index("--out") + 1]))
    if len(argv) == 5 and argv[1] == "judge":
        return judge(pathlib.Path(argv[2]), argv[3], argv[4])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
