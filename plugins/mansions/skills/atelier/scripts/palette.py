#!/usr/bin/env python3
"""Colour plan for one piece: the brand's hues, moved by the piece's register, across its pages, checked.

  python palette.py --register relief --harmony analogous --arc dawn --pages 6 [--brand <tokens.css>] [--out <folder>]
  python palette.py ... --field-page 3               # page 3 (1-based; repeat or list for more) is the full-colour field page, any arc
  python palette.py --taste <palette-id> ...         # start from one of taste-skill's 56 curated palettes instead
  python palette.py --list-taste [tag]               # list those palettes (vendor/taste-skill/library/palettes.json)

Connotation is carried mainly by lightness (brighter reads more pleasant), chroma (more saturated reads more
arousing) and temperature, which have stronger evidence than hue clichés (Valdez and Mehrabian 1994; hue meaning
varies by culture, Jonauskaite et al. 2020). So the brand's hues stay, and the register moves lightness, chroma
and proportion; the arc moves them across pages, like a film's colour script. Every colour custom property in the
brand file is read and grouped into hue families; every accent hue comes from a family (only --taste may add hues). Without --brand
or --taste the piece gets its own palette, made from the register, harmony and arc (data/colour.json "own"), kept SPEC_MIN and ACC_MIN
in OKLab away from the specimen palette (assets/tokens.css) and out of the clusters of references/tells.md.
All maths in OKLab/OKLCH (Ottosson 2020), perceptually even, with gamut clipping by chroma.

Writes <out>/palette.css (.pg-1 ... .pg-N set --ground, --text, --text-2, --accent, --accent-2) and
<out>/colour-plan.md (harmony, arc, per-page values, WCAG contrast, colour-vision checks, warnings, the reasoning).
Exit 1 if any page fails contrast or an accent vanishes for a colour-vision type. WARN lines (a common cluster, an arc
step too small to see) and the override line do not change the exit code. Exit 2 and one line on stderr for an input that
cannot be planned (an unknown register, harmony or arc, a missing brand file, --pages under 1). Standard library only.
"""
import argparse
import json
import math
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
SKILL = pathlib.Path(__file__).resolve().parent.parent
DATA = SKILL / "data"
MACHADO = {
    "protan": (0.152286, 1.052583, -0.204868, 0.114503, 0.786281, 0.099216, -0.003882, -0.048116, 1.051998),
    "deutan": (0.367322, 0.860646, -0.227968, 0.280085, 0.672501, 0.047413, -0.011820, 0.042940, 0.968881),
    "tritan": (1.255528, -0.076749, -0.178779, -0.078411, 0.930809, 0.147602, 0.004733, 0.691367, 0.303900),
}
HUE_MIN_C = 0.02    # OKLCH chroma below this is a tinted neutral (paper, ink, steel), not a brand hue
FAMILY_GAP = 25     # degrees: hues closer than this belong to one family
HUE_TOL = 8         # degrees a family may stretch past its outermost token
GREEN = (105, 172)  # OKLCH hue band of greens, kept clear unless the brand has a family in it
WARM = 70           # OKLCH hue of amber, the target of "warmer"
NUDGE = 15          # degrees a warm start may lean inside the base family when the brand has no warm hue
NEAR = 15           # degrees: two accents closer than this read as one hue
LIFT = 0.10         # lightness the warm end of a cooldown gains on dark grounds (loses on paper): contrast high early, calm late
ACTS = 3            # a temperature arc moves in at most this many acts (warm, middle, calm); pages inside one act share an accent
ROLES = ("night", "paper", "ink", "cream")    # the ground and text slots of a brand file, never its accent
HOUSE_NAMES = ("primary", "brand", "accent")  # what a brand file calls its main colour when it has no --house
STEP_MIN = 0.04     # OKLab distance between the accents of two acts: twice the just-noticeable difference of 0.02 (CSS Color 4,
                    # deltaEOK), because pages are seen one after another, not side by side; the factor 2 is our choice, not measured
L_STEP = 0.005      # lightness an unbranded neutral steps by once its chroma is at OWN_C, until it is clear of the specimen palette and the clusters
SPEC_MIN = 0.04     # OKLab distance an unbranded piece's ground and text keep from the specimen palette's (assets/tokens.css) in the same role:
                    # twice the just-noticeable difference, as STEP_MIN, because a critic sees the page and the specimen one after the other
ACC_MIN = 0.10      # OKLab distance an unbranded accent keeps from every specimen accent (house, teal, teal-lit, amber, glow): five times the
                    # just-noticeable difference, so it reads as another colour, not a shade of theirs (the 30 Oct 2026 run's #234798 was 0.05 from #143ca1); our choice
OWN_C = 0.016       # the most chroma an unbranded paper or cream takes while it steps away from the specimen's (a tinted stock, not a pastel);
                    # past it, lightness moves. A night or an ink may take twice as much: a dark holds a tint without turning into a colour
ACC_TEXT = 0.20     # OKLab distance an unbranded accent keeps from its page's text colour, so it reads as a colour and not as more ink. In the 30 Oct 2026
                    # run the critic read a madder accent 0.160 from its brown ink as ink; accents 0.221 and 0.239 from theirs read as accents. Our choice
GOLDEN = 0.6180339887   # spreads the harmony x arc deals over a register's hue band (the golden-ratio sequence leaves no clumps)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def rgb_to_hex(c):
    return "#" + "".join(f"{round(max(0, min(1, v)) * 255):02x}" for v in c)


def lin(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def delin(v):
    return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def to_oklab(rgb):
    r, g, b = (lin(v) for v in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(x) ** (1 / 3), x) for x in (l, m, s))
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def from_oklab(lab):
    L, a, b = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return (r, g, bb)


def to_lch(rgb):
    L, a, b = to_oklab(rgb)
    return (L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360)


def from_lch(L, C, H):
    """OKLCH to sRGB, reducing chroma until the colour fits the sRGB gamut."""
    for _ in range(40):
        a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
        lr = from_oklab((L, a, b))
        if all(-1e-4 <= v <= 1 + 1e-4 for v in lr):
            return tuple(delin(max(0, min(1, v))) for v in lr)
        C *= 0.9
    return tuple(delin(max(0, min(1, v))) for v in from_oklab((L, 0, 0)))


def luminance(rgb):
    r, g, b = (lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    x, y = luminance(a), luminance(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def simulate(rgb, m):
    r, g, b = (lin(v) for v in rgb)
    out = (m[0] * r + m[1] * g + m[2] * b, m[3] * r + m[4] * g + m[5] * b, m[6] * r + m[7] * g + m[8] * b)
    return tuple(delin(max(0, min(1, v))) for v in out)


def delta_e(a, b):
    p, q = to_oklab(a), to_oklab(b)
    return math.dist(p, q)


def read_tokens(css):
    """Every `--name: #hex` colour custom property (#rgb, #rrggbb, or #rrggbbaa without its alpha)."""
    out = {}
    for name, h in re.findall(r"--([\w-]+)\s*:\s*#([0-9a-fA-F]+)\b", css):
        h = "".join(c * 2 for c in h[:3]) if len(h) in (3, 4) else h
        if len(h) in (6, 8):
            out[name] = "#" + h[:6]
    return out


def gap(a, b):
    """Unsigned distance between two hue angles, 0 to 180."""
    return abs((a - b + 180) % 360 - 180)


def hue_families(colours, accent):
    """Group the brand's chromatic colours into hue families, each {mid, half, names}. The accent always counts."""
    pts = []
    for name, c in colours.items():
        _, ch, h = to_lch(hex_to_rgb(c))
        if ch >= HUE_MIN_C or c == accent:
            pts.append((h, name))
    pts.sort()
    groups = []
    for p in pts:
        if groups and p[0] - groups[-1][-1][0] <= FAMILY_GAP:
            groups[-1].append(p)
        else:
            groups.append([p])
    if len(groups) > 1 and groups[0][0][0] + 360 - groups[-1][-1][0] <= FAMILY_GAP:
        groups[0] = groups.pop() + groups[0]
    fams = []
    for g in groups:
        rad = [math.radians(h) for h, _ in g]
        mid = math.degrees(math.atan2(sum(map(math.sin, rad)), sum(map(math.cos, rad)))) % 360
        fams.append({"mid": mid, "half": max(gap(h, mid) for h, _ in g) + HUE_TOL, "names": [n for _, n in g]})
    return fams


def snap(h, fams):
    """The hue nearest to h that a brand family owns: h itself inside a family, else the edge of the nearest one."""
    f = min(fams, key=lambda x: max(0, gap(h, x["mid"]) - x["half"]))
    d = (h - f["mid"] + 180) % 360 - 180
    return h % 360 if abs(d) <= f["half"] else (f["mid"] + math.copysign(f["half"], d)) % 360


def in_green(h):
    return GREEN[0] <= h % 360 <= GREEN[1]


def warm_hue(H0, fams):
    """Where a warm start sits: the brand's own warm family when it has one; else a nudge toward amber inside the base
    family, held clear of the green band unless the brand has a green family of its own."""
    warm = [f for f in fams if gap(f["mid"], WARM) <= 45]
    if warm:
        return min(warm, key=lambda f: gap(f["mid"], WARM))["mid"]
    sign = 1 if (WARM - H0 + 180) % 360 - 180 > 0 else -1
    h = snap(H0 + sign * NUDGE, [min(fams, key=lambda f: gap(f["mid"], H0))])
    if in_green(h) and not any(in_green(f["mid"]) for f in fams):
        h = GREEN[1] if sign < 0 else GREEN[0]
    return h


def temperature_hue(H0, W, t):
    """Accent hue at arc position t (0 warm end, 1 the brand's hue). A warm family apart from the base one is held for
    the first half and then dropped, because a hue ramp between two families passes through hues the brand does not own
    (between teal and amber, the green band); a nudge inside the base family eases back."""
    if gap(W, H0) > FAMILY_GAP:
        return W if t < 0.5 else H0
    return (H0 + ((W - H0 + 180) % 360 - 180) * (1 - t)) % 360


def pick_house(v):
    """The colour that stands for a brand whose file has no --house: the one named primary, brand or accent (the name says
    where it is used, which a tokens file records nowhere else), else the most chromatic one. The ground and text slots count
    only when nothing else has a hue. (name, named), or (None, False) when every colour is a grey."""
    chroma = {n: to_lch(hex_to_rgb(c))[1] for n, c in v.items()}
    chroma = {n: c for n, c in chroma.items() if c >= HUE_MIN_C}
    chroma = {n: c for n, c in chroma.items() if n not in ROLES} or chroma
    named = next((n for k in HOUSE_NAMES for n in chroma if n == k or n.endswith("-" + k)), None)
    return named or max(chroma, key=chroma.get, default=None), bool(named)


def brand_from_tokens(path):
    v = read_tokens(pathlib.Path(path).read_text(encoding="utf-8"))
    accent, note, neutral = v.get("house"), "", False
    if not accent:
        pick, named = pick_house(v)
        if pick:
            accent = v[pick]
            note = (f"NOTE no --house in the brand file: the accent hue is that of --{pick} ({accent}, {to_lch(hex_to_rgb(accent))[2]:.0f} deg), "
                    f"{'the colour the file names for the brand' if named else 'its most chromatic colour'}. Add --house to choose another.")
        else:
            accent, neutral = v.get("ink", "#222222"), True
            note = ("NOTE no --house in the brand file and no chromatic colour among its #hex values: the accent is a neutral grey, "
                    "no hue is added. Add --house to give the brand one.")
    return {"dark": v.get("night", "#111111"), "paper": v.get("paper", "#f5f3ee"), "ink": v.get("ink", "#222222"),
            "cream": v.get("cream", "#f5f5f2"), "accent": accent, "accent_lit": v.get("teal-lit", accent),
            "families": hue_families({**v, "accent": accent}, accent), "taste": False, "neutral": neutral, "note": note}


def brand_from_taste(pid):
    pals = json.loads((SKILL / "vendor" / "taste-skill" / "library" / "palettes.json").read_text(encoding="utf-8"))
    p = next((x for x in pals if x["id"] == pid), None)
    if not p:
        sys.exit(f"no taste palette '{pid}'; try --list-taste")
    bg, ink = p["bg"], p["ink"]
    light = luminance(hex_to_rgb(bg)) > 0.4
    field = (p.get("fields") or [{}])[0]
    return {"dark": bg if not light else field.get("bg", "#111111"), "paper": bg if light else field.get("bg", "#f5f3ee"),
            "ink": ink if light else field.get("ink", "#222222"), "cream": ink if not light else field.get("ink", "#f5f5f2"),
            "accent": p["accent"], "accent_lit": p["accent"], "_note": p.get("note", ""),
            "families": hue_families({"accent": p["accent"]}, p["accent"]), "taste": True}


def specimen_colours():
    """The specimen palette by role: assets/tokens.css, which every specimen page is drawn in. An unbranded piece keeps away from it."""
    t = read_tokens((SKILL / "assets" / "tokens.css").read_text(encoding="utf-8"))
    return {"ground": [hex_to_rgb(t[k]) for k in ("paper", "night", "house")],
            "text": [hex_to_rgb(t[k]) for k in ("ink", "cream")],
            "accent": [hex_to_rgb(t[k]) for k in ("house", "teal", "teal-lit", "amber", "glow")]}


def step_clear(L, C, H, avoid, grounds, dl, cap=OWN_C):
    """A neutral at OKLCH (L, C, H), moved until it is SPEC_MIN or more from every colour in avoid and clear of every cluster ground by a margin
    (SPEC_MIN past its distance, NEAR degrees past its hue range): its chroma rises to cap first (a tinted stock, like a coloured paper), then
    its lightness moves by dl. In the 30 Oct 2026 run a warm paper 0.034 from cluster 1's cream, one degree under its hue range, read as cream."""
    for _ in range(200):
        c = hex_to_rgb(rgb_to_hex(from_lch(L, C, H)))   # judged as written, after rounding to #rrggbb
        if min(delta_e(c, a) for a in avoid) >= SPEC_MIN and not any(in_ground(c, gd, SPEC_MIN, NEAR) for gd in grounds):
            break
        if C < cap:
            C = min(cap, C + 0.002)
        else:
            L += dl
    return c


def clear_accent(L, C, H, avoid, text=None, ground=None):
    """An unbranded accent at OKLCH (L, C, H), moved the least way until it is ACC_MIN or more from every specimen accent: its lightness
    down by 0.05 or 0.10 (a pale colour holds little chroma, so a step down often clears it and keeps the hue), or its hue turned up to
    60 degrees either way. One lightness step of 0.05 costs as much as a 6 degree turn; the cheapest move that clears wins. With the page's
    text and ground it must also sit ACC_TEXT or more from the text and keep 4.5:1 on the ground, and lightness may move further: up by up to
    0.15 (on paper the ink is dark, so the accent moves up, away from it) or down by up to 0.20 (on a dark ground the text is light). With no
    move that does both, the first that clears ACC_MIN wins."""
    moves = sorted((abs(dh) / 3 + abs(dl) / 0.025, dl < 0, dh, dl) for dh in range(-60, 61, 3) for dl in ((0, 0.05, 0.10) if text is None else (0, 0.05, 0.10, 0.15, 0.20, -0.05, -0.10, -0.15)))
    first = None
    for *_, dh, dl in moves:
        c = hex_to_rgb(rgb_to_hex(from_lch(L - dl, C, (H + dh) % 360)))
        if min(delta_e(c, a) for a in avoid) < ACC_MIN:
            continue
        first = first or c
        if text is None or (delta_e(c, text) >= ACC_TEXT and contrast(c, ground) >= 4.5):
            return c
    return first or c


def own_brand(register, harmony, arc):
    """The palette of a piece with no --brand, made for it from the dealt register, harmony and arc (data/colour.json "own"). The register
    gives a hue band for the accent and a hue for the neutrals; the harmony and the arc choose the place in the band, so another harmony
    or arc gives another accent. The paper, night, ink and cream are tinted neutrals at that hue, stepped SPEC_MIN or more away from the
    specimen palette (assets/tokens.css) and out of the clusters of references/tells.md; plan() turns each accent ACC_MIN or more away
    from the specimen accents. Without this, every unbranded page wore the specimens' own paper, ink and blue (the 30 Oct 2026 runs)."""
    colour = json.loads((DATA / "colour.json").read_text(encoding="utf-8"))
    own, spec = colour["own"], specimen_colours()
    r = own["registers"][register]
    k = [h["id"] for h in colour["harmonies"]].index(harmony) * len(colour["arcs"]) + [x["id"] for x in colour["arcs"]].index(arc)
    lo, hi = r["accent"]
    shift = (k * GOLDEN) % 1 * ((hi - lo) % 360)
    H, Hn = (lo + shift) % 360, (r["neutral"] + shift) % 360
    grounds = [c["ground"] for c in colour["clusters"]]
    out = {"paper": step_clear(0.94, r["neutral_C"], Hn, spec["ground"], grounds, -L_STEP),
           "dark": step_clear(0.235, r["neutral_C"] + 0.01, Hn, spec["ground"], grounds, L_STEP, 2 * OWN_C),
           "ink": step_clear(0.28, r["neutral_C"] + 0.01, Hn, spec["text"], [], L_STEP, 2 * OWN_C),
           "cream": step_clear(0.94, r["neutral_C"], Hn, spec["text"], [], -L_STEP)}
    out = {k: rgb_to_hex(v) for k, v in out.items()}
    house, warm = rgb_to_hex(from_lch(0.45, r["C"], H)), rgb_to_hex(from_lch(0.6, 0.12, own["warm"]))
    note = (f"NOTE no --brand: this piece's own palette, made from register {register} (accent hues {lo} to {hi} deg, neutrals at "
            f"{r['neutral']} deg: {r['why']}), harmony {harmony} and arc {arc}: accent hue {H:.0f} deg, paper {out['paper']}, night {out['dark']}, "
            f"ink {out['ink']}, cream {out['cream']}. Each ground and text colour is {SPEC_MIN} or more OKLab from the specimens' (assets/tokens.css) "
            f"and each accent {ACC_MIN} or more from theirs, and no ground is in a cluster of references/tells.md. Pass your tokens.css with --brand to use your own.")
    return {**out, "accent": house, "accent_lit": house, "families": hue_families({"house": house, "warm": warm}, house),
            "taste": False, "own": True, "neutral": False, "note": note, "spec": spec, "neutral_hue": Hn}


def in_ground(g, gd, margin=0, hue_pad=0):
    """True when a ground colour sits in a cluster's ground: within its OKLab distance, and in its hue range with some chroma when it has one.
    margin and hue_pad widen both, for the own palette, which keeps clear of a cluster and does not stop at its edge."""
    _, gc, gh = to_lch(g)
    return delta_e(g, hex_to_rgb(gd["hex"])) <= gd["de"] + margin and ("hue" not in gd or (gd["hue"][0] - hue_pad <= gh <= gd["hue"][1] + hue_pad and gc >= gd["min_c"]))


def cluster_notes(rows, clusters, branded):
    """Lines for a plan whose ground (and accent) sit near a cluster of references/tells.md; see data/colour.json "clusters"."""
    out = []
    for c in clusters:
        hits = []
        gd = c["ground"]
        for r in rows:
            if not in_ground(r["g"], gd):
                continue
            _, C, H = to_lch(r["acc"])
            acc = any(x["hue"][0] <= H <= x["hue"][1] and C >= x["min_c"] for x in c["accent"])
            if acc or c["ground_alone"]:
                hits.append((r, acc))
        if not hits:
            continue
        pages = ", ".join(str(r["page"]) for r, _ in hits)
        both = any(acc for _, acc in hits)
        what = f"ground {rgb_to_hex(hits[0][0]['g'])}" + (" and accent are" if both else " is")
        if branded:
            tail = "matches a common cluster; fine if it is your brand."
        else:
            tail = "free axes should not land here. Move the ground or the accent" + ("." if both else f", and keep off {c['also']}.")
        out.append(f"{'NOTE' if branded else 'WARN'} page {pages}: {what} in cluster {c['id']} of references/tells.md ({c['name']}); {tail}")
    return out


def step_notes(rows):
    """A WARN line for each step of a temperature arc, where one act gives way to the next, whose accents sit closer than
    STEP_MIN in OKLab (a field page has its own colour, so it is skipped)."""
    weak = []
    for a, b in zip(rows, rows[1:]):
        d = delta_e(a["acc"], b["acc"])
        if a["act"] != b["act"] and "field" not in (a["ground"], b["ground"]) and d < STEP_MIN:
            weak.append(f"{a['page']} to {b['page']} ({d:.3f})")
    if not weak:
        return []
    return [f"WARN arc steps too small to see, pages {', '.join(weak)}: consecutive accents of a visible arc need an OKLab distance of "
            f"{STEP_MIN} or more. Use a register that allows more chroma, or drop the arc."]


def plan(brand, register, harmony, arc, pages, base=None, field_pages=(), branded=False):
    colour = json.loads((DATA / "colour.json").read_text(encoding="utf-8"))
    regs = json.loads((DATA / "registers.json").read_text(encoding="utf-8"))
    rec_id = regs[register]["colour"]["recipe"]
    rec = colour["recipes"].get(rec_id, {})
    hmony = next(h for h in colour["harmonies"] if h["id"] == harmony)
    info = {"override": None, "lines": [brand["note"]] if brand.get("note") else []}
    if rec.get("harmony") == "monochrome" and harmony != "monochrome":
        # a monochrome recipe keeps its accent to a sliver on one thing: a second accent colour has no place to go
        share = f", accent {rec['accent_share']} of the area" if rec.get("accent_share") else ""
        info["override"] = (f"harmony {harmony} overridden by register {register}: recipe {rec_id} is monochrome{share}, "
                            "so one accent hue applies and there is no accent-2.")
        hmony = next(h for h in colour["harmonies"] if h["id"] == "monochrome")
    fams = brand["families"]
    own = brand.get("own")
    L0, C0, H0 = to_lch(hex_to_rgb(brand["accent"]))
    if rec.get("temperature") == "warm":
        # a warm recipe: a piece's own palette is made warm (its neutrals and its accent band, data/colour.json "own"); a brand's are the brand's
        if own:
            info["lines"].append(f"NOTE warm neutrals and a warm accent (recipe {rec_id}: {rec.get('ground', 'paper, warmed')}, temperature warm): "
                                 f"the paper, ink and night are tinted at hue {brand['neutral_hue']:.0f} deg and the accent is at {H0:.0f} deg, "
                                 f"chroma {rec.get('accent_C')}, both on the warm side.")
        else:
            info["lines"].append(f"NOTE recipe {rec_id} asks for warm neutrals ({rec.get('ground', 'paper, warmed')}): the "
                                 f"{'taste palette' if brand['taste'] else 'brand'}'s own paper, ink and night are kept.")
    # register sets accent chroma and lightness; brand hue stays
    cr = rec.get("accent_C")
    if isinstance(cr, list):
        C_acc = max(cr[0], min(cr[1], C0)) if C0 else cr[0]
    elif cr == "max in gamut":
        C_acc = max(C0, 0.16)
    else:
        C_acc = C0
    neutral = brand.get("neutral")
    if neutral:
        C_acc = 0   # a brand of greys has no hue to give an accent: the accent, accent-2 and the field stay grey
    # every harmony hue comes from a brand family; only a taste palette (one accent hue) or a piece's own palette may add hues
    hues = [(H0 + d) % 360 for d in hmony["hues"]]
    if own:   # the band gives the accent; the harmony's other hues follow it, the warmer one first under a warm recipe
        hues = [H0] + sorted(((H0 + d) % 360 for d in hmony["hues"] if d), key=lambda h: gap(h, WARM) if rec.get("temperature") == "warm" else 0)
    elif not brand["taste"]:
        hues = [snap(h, fams) for h in hues]
    warming = rec_id == "warm-to-cool-arc" or arc == "cooldown"
    W = warm_hue(H0, fams) if warming else H0
    rows = []
    for i in range(pages):
        t = i / max(1, pages - 1)
        acts = min(pages, ACTS)
        act = i * acts // pages
        u = act / (acts - 1) if acts > 1 else 0   # where the temperature arc stands: 0 warm end, 1 calm end
        # the direction's ground (--ground, from the genome) wins over the register's; the arc then moves away from it
        ground = base or ("dark" if rec.get("ground") == "dark" else "paper")
        if arc == "dawn":
            ground = "dark" if t < 0.5 else "paper"
        elif arc == "chapters":
            ground = ["dark", "paper", "field"][i % 3]
        elif arc == "single-flash" and i == round((pages - 1) * 0.6) and not field_pages:
            ground = "field"
        if i + 1 in field_pages:
            ground = "field"
        g_rgb = hex_to_rgb(brand["dark"] if ground == "dark" else brand["paper"])
        if ground == "field":
            g_rgb = from_lch(0.42, 0 if neutral else max(0.06, C_acc * 0.8), H0)
        text = hex_to_rgb(brand["cream"] if ground in {"dark", "field"} else brand["ink"])
        # accent lightness must separate from the ground: light accent on dark, deep accent on paper
        on_dark = ground in {"dark", "field"}
        aL = 0.82 if on_dark else 0.42
        c_mult = 1.0
        if arc == "cooldown":
            c_mult = 1.25 - 0.6 * u
        elif arc == "dawn":
            c_mult = 0.7 + 0.5 * t
        hue = hues[0]
        if warming:
            # warmer early by the brand's own warm hue (or a nudge inside its hue), plus more contrast; never through the greens
            hue = temperature_hue(H0, W, u)
            aL += (LIFT if on_dark else -LIFT) * (1 - u)
        mix = (lambda L, C, h: clear_accent(L, C, h, brand["spec"]["accent"], text, g_rgb)) if own else from_lch   # an own accent keeps off the specimen's and off the ink
        acc = mix(aL, C_acc * c_mult, hue)
        if ground == "field":
            acc = hex_to_rgb(brand["cream"])
        acc2 = None
        if len(hues) > 1:
            h2 = hues[1]
            if gap(h2, hue) < NEAR <= gap(H0, hue):
                h2 = H0   # a warm page: the pair is the warm hue and the brand's own
            if gap(h2, hue) < NEAR:   # the brand has no second hue there: a quieter step of the same one
                acc2 = mix(aL + (-0.1 if on_dark else 0.1), C_acc * 0.5, h2)
            else:
                acc2 = mix(aL, C_acc * 0.9, h2)
        text2 = tuple(v * 0.82 + w * 0.18 for v, w in zip(text, g_rgb))
        rows.append({"page": i + 1, "act": act, "ground": ground, "g": g_rgb, "text": text, "text2": text2, "acc": acc, "acc2": acc2})
    near_ink = [str(r["page"]) for r in rows if own and r["ground"] != "field" and delta_e(r["acc"], r["text"]) < ACC_TEXT]
    if near_ink:
        info["lines"].append(f"WARN page {', '.join(near_ink)}: the accent sits under {ACC_TEXT} OKLab from the text colour, so it may read as more ink; "
                             "no lightness or hue step kept 4.5:1 on the ground. Draw the accent larger, or deal another register.")
    if warming:
        info["lines"] += step_notes(rows)
    info["lines"] += cluster_notes(rows, colour["clusters"], branded)
    if brand["taste"] and len(hues) > 1:
        info["lines"].append(f"NOTE taste palette: accent-2 hue {hues[1]:.0f} is new (the harmony's offset from the palette's one accent hue {H0:.0f}); only --taste adds hues.")
    info["hues"] = {"families": [(round(f["mid"]), f["names"]) for f in fams], "accent": H0, "warm": W if warming else None, "harmony": hues}
    return rec_id, rec, hmony, rows, regs[register], colour, info


def die(msg):
    """An input that cannot be planned: one line on stderr and exit 2, so that exit 1 keeps meaning 'the plan has a page to fix'."""
    print(f"palette.py: error: {msg}", file=sys.stderr)
    sys.exit(2)


def main():
    colour = json.loads((DATA / "colour.json").read_text(encoding="utf-8"))
    ap = argparse.ArgumentParser()
    ap.error = die
    ap.add_argument("--register", default="craft-pride", choices=list(json.loads((DATA / "registers.json").read_text(encoding="utf-8"))))
    ap.add_argument("--harmony", default="monochrome", choices=[x["id"] for x in colour["harmonies"]])
    ap.add_argument("--arc", default="steady", choices=[x["id"] for x in colour["arcs"]])
    ap.add_argument("--pages", type=int, default=1, help="how many pages, 1 or more")
    ap.add_argument("--brand", help="the brand's tokens.css (only #hex colours are read); default: the piece's own palette, made from the register, harmony "
                    "and arc and kept off the specimens' colours (data/colour.json \"own\"). The accent is its --house. With none: the colour the file names primary, brand or accent, else its most chromatic one, "
                    "and a NOTE says which; a file of greys only gets a neutral grey accent (no hue is added) and a NOTE")
    ap.add_argument("--taste")
    ap.add_argument("--list-taste", nargs="?", const="")
    ap.add_argument("--ground", choices=["dark", "paper", "field"], help="the direction's ground (the genome's 'ground'); default: the register's")
    ap.add_argument("--field-page", type=int, nargs="+", action="extend", default=[], metavar="N",
                    help="1-based page(s) that are the full-colour field page, for any arc (the genome's 'field' words); default: the arc decides")
    ap.add_argument("--out", default=".")
    a = ap.parse_args()
    if a.list_taste is not None:
        pals = json.loads((SKILL / "vendor" / "taste-skill" / "library" / "palettes.json").read_text(encoding="utf-8"))
        for p in pals:
            if not a.list_taste or a.list_taste in p.get("tags", []):
                print(f"{p['id']:28} {p['bg']} {p['ink']} {p['accent']}  {', '.join(p.get('tags', []))}")
        return 0
    if a.pages < 1:
        die(f"--pages {a.pages}: a piece has 1 page or more")
    if a.brand and not pathlib.Path(a.brand).is_file():
        die(f"--brand {a.brand}: no such file")
    bad = [n for n in a.field_page if not 1 <= n <= a.pages]
    if bad:
        sys.exit(f"--field-page {bad[0]} is outside the {a.pages} page(s): pages count from 1")
    brand = brand_from_taste(a.taste) if a.taste else brand_from_tokens(a.brand) if a.brand else own_brand(a.register, a.harmony, a.arc)
    rec_id, rec, hmony, rows, reg, colour, info = plan(brand, a.register, a.harmony, a.arc, a.pages, a.ground, a.field_page, bool(a.brand) and not a.taste)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    h = info["hues"]
    hue_line = ("Hues: none, the brand has no chromatic colour, so every accent is a neutral grey." if brand.get("neutral") else
                "Hues: " + ("a taste palette has one hue, so the harmony may add hues" if brand["taste"] else
                            "this piece's own palette (no --brand): the register's band gives the accent and the harmony adds its other hues" if brand.get("own") else
                            "brand families " + "; ".join(f"{m} deg ({', '.join(n)})" for m, n in h["families"]) + ", and every accent hue comes from one")
                + f". Accent {h['accent']:.0f} deg" + (f", warm end {h['warm']:.0f} deg" if h["warm"] is not None else "")
                + (f", accent-2 {h['harmony'][1]:.0f} deg" if len(h["harmony"]) > 1 else "") + ".")
    css = [f"/* atelier palette: register {a.register} ({rec_id}), harmony {hmony['id']}"
           + (f" (dealt {a.harmony})" if info["override"] else "") + f", arc {a.arc}. Generated by palette.py. */"]
    md = [f"# Colour plan", "", f"Register **{a.register}**: {reg['feeling']}. Recipe `{rec_id}`: {json.dumps(rec)}.",
          f"Harmony **{hmony['id']}** (hue offsets {hmony['hues']}): {hmony['when']}. Risk: {hmony['risk']}."]
    md += ["", info["override"], ""] if info["override"] else []
    md += [f"Arc **{a.arc}**: {next((x['pages'] for x in colour['arcs'] if x['id'] == a.arc), '')}."
           + (f" Field page(s) {', '.join(map(str, sorted(a.field_page)))} chosen with --field-page." if a.field_page else ""),
           f"Ground: **{a.ground or 'from the register'}**" + (" (the direction's ground; the arc moves from it)." if a.ground else "."),
           hue_line, "",
          "Why: " + " ".join(f"{d['id']}: {d['use']} ({d['evidence']})." for d in colour["dimensions"]), "",
          "| page | ground | text | accent | text contrast | accent contrast | colour-vision check |", "|---|---|---|---|---|---|---|"]
    fails = 0
    for r in rows:
        tc, ac = contrast(r["text"], r["g"]), contrast(r["acc"], r["g"])
        cvd = []
        for name, m in MACHADO.items():
            sa, sg = simulate(r["acc"], m), simulate(r["g"], m)
            if contrast(sa, sg) < 1.6 and delta_e(sa, sg) < 0.12:
                cvd.append(f"accent vanishes for {name}")
        status = "ok" if tc >= 4.5 and not cvd else "FIX"
        if status == "FIX":
            fails += 1
        md.append(f"| {r['page']} | {r['ground']} {rgb_to_hex(r['g'])} | {rgb_to_hex(r['text'])} | {rgb_to_hex(r['acc'])} | {tc:.1f}:1 | {ac:.1f}:1 | {'; '.join(cvd) or 'ok'} |")
        css.append(f".pg-{r['page']} {{ --ground: {rgb_to_hex(r['g'])}; --text: {rgb_to_hex(r['text'])}; --text-2: {rgb_to_hex(r['text2'])}; --accent: {rgb_to_hex(r['acc'])};"
                   + (f" --accent-2: {rgb_to_hex(r['acc2'])};" if r["acc2"] else "") + " }")
    md += ["", "Checks:"] + [f"- {x}" for x in info["lines"] or ["none to report."]] + ["",
           "Proportion: the ground covers 70 to 90% of each page, the accent under 5% and on ONE thing (the thing to remember).",
           "Meaning: " + colour["hue_associations"]["_caveat"]]
    (out / "palette.css").write_text("\n".join(css) + "\n", encoding="utf-8")
    (out / "colour-plan.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    head = next(i for i, line in enumerate(md) if line.startswith("| page |"))
    print("\n".join(([info["override"]] if info["override"] else []) + md[head:head + 2 + len(rows)] + info["lines"]))
    print(f"palette.css and colour-plan.md written to {out}" + (f"; {fails} page(s) need a fix" if fails else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
