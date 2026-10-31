#!/usr/bin/env python3
"""Fetch an open-licensed font family from Google Fonts into your project, with its licence.

  python get_font.py "Bricolage Grotesque" [--axes "opsz,wdth,wght@12..96,75..100,200..800"] [--out fonts]

Downloads the latin and latin-ext woff2 files, writes <out>/<family>.css with local @font-face rules (load it
before your brand file), and fetches the family's OFL.txt from github.com/google/fonts. Choose type on purpose
(references/type.md), not the family you would use for anything. Standard library only.
"""
import argparse
import pathlib
import re
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return data if binary else data.decode("utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("family")
    ap.add_argument("--axes", default="wght@100..900")
    ap.add_argument("--out", default="fonts")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fam = a.family.strip()
    q = urllib.parse.quote(fam).replace("%20", "+")
    css = None
    for axes in (a.axes, "wght@400..700", "wght@400;700", ""):
        url = f"https://fonts.googleapis.com/css2?family={q}" + (f":{axes}" if axes else "") + "&display=swap"
        try:
            css = get(url)
            break
        except Exception:  # noqa: BLE001  try a narrower axis range
            continue
    if not css:
        print(f"could not fetch {fam} from Google Fonts")
        return 1
    blocks = re.findall(r"/\* ([\w-]+) \*/\s*(@font-face \{.*?\})", css, flags=re.S)
    slug = re.sub(r"[^a-z0-9]+", "-", fam.lower()).strip("-")
    local = []
    n = 0
    for subset, block in blocks:
        if subset not in {"latin", "latin-ext"}:
            continue
        src = re.search(r"url\((https://[^)]+)\)", block).group(1)
        style = re.search(r"font-style: (\w+)", block).group(1)
        name = f"{slug}-{subset}-{style}-{n}.woff2"
        (out / name).write_bytes(get(src, binary=True))
        local.append(block.replace(src, name))
        n += 1
    (out / f"{slug}.css").write_text(f"/* {fam}, from Google Fonts. Licence: {slug}-OFL.txt */\n" + "\n".join(local) + "\n", encoding="utf-8")
    lic = "(licence not found: check fonts.google.com)"
    for folder in ("ofl", "apache", "ufl"):
        try:
            lic = get(f"https://raw.githubusercontent.com/google/fonts/main/{folder}/{fam.lower().replace(' ', '')}/{'OFL.txt' if folder == 'ofl' else 'LICENSE.txt'}")
            break
        except Exception:  # noqa: BLE001
            continue
    (out / f"{slug}-OFL.txt").write_text(lic, encoding="utf-8")
    print(f"{fam}: {n} file(s) and {slug}.css in {out}. In CSS: font-family: \"{fam}\". Licence saved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
