#!/usr/bin/env python3
"""The composer: a graded, memory-driven pipeline that makes every piece different on purpose.

  python compose.py new <slug> --topic "..." [--medium carousel|image|video|text|slide] [--scope full|design|quick] [--brand tokens.css]
  python compose.py adopt <slug> --angle "..." --operator <id> --evidence <file> [--pin direction=receipt,register=dry]   # design scope
  python compose.py next <slug>                  # what to do now (always start here)
  python compose.py deal <slug> lenses|angles|genome [--seed N] [--any-type] [--pin register=warmth]
  python compose.py choose <slug> angle <n>      # which dealt operator's angle wins (quick scope: the one you used)
  python compose.py grade <slug> <stage> --scores "novelty=8,truth=9,..." --notes notes.md --by self|critic [--evidence verdict.md] [--swap pass|fail] [--folder DIR]
  python compose.py similar <slug> "<one-line angle>"   # novelty of a sentence against everything made before
  python compose.py status <slug>
  python compose.py scaffold <slug> [--out visual.html] [--force]   # start the page: for an image or a carousel a composition start on the grid (each page set up for its dealt layout word, not the specimen's frame), on the palette.css roles and your --brand, links made absolute, the logo slot filled from the brand file's --logo or removed
  python compose.py deliver <slug>               # only when every stage has passed; writes the memory
  python compose.py coverage                     # how much of the creative space has been used

A slug is 1 to 64 characters: lower-case letters, digits, '.', '_' or '-', starting with a letter or digit. It becomes a folder name.
Stages, in order: atoms, lenses, angles, genome, sections, copy, visual, final (data/rubrics.json).
Scopes: full (all eight stages: 8 to 12 atoms, 3 lenses, and one angle for EACH dealt operator, up to 6, graded together by
the story-editor), design (the host system owns the words: adopt an angle, then the genome), quick (one image, four stages:
3 to 5 atoms; 3 operators are dealt and the author picks ONE of them and writes ONE angle, which the author grades; genome;
visual; only the visual needs a critic's verdict file).
Each stage is graded 1 to 10 per criterion; every score needs a "because" line in the notes file that quotes or
locates evidence. Total = weighted mean after caps, one decimal, never rounded up. Below the threshold the stage
is recreated (a fresh deal that excludes what failed) or revised, up to max_attempts, then escalated.
Stages marked independent must be graded by a critic agent (--by critic), not by the author, and the grade must carry the
critic's verdict file (--evidence): it is checked, hashed and written to memory with the piece. The file needs a verdict
or score line. A FAIL or REVISE verdict can never pass the stage; per-criterion scores or a total in the file must equal
the --scores typed (the author cannot grade the critic's file upward). The visual stage also needs a fresh render: audit.json
saying PASS and page-NN.png, each newer than the page's HTML, in the folder scaffold wrote the page into (--folder is for a page built without
scaffold). The grade stores the sha256 of the verdict file, of visual.html and of every page-NN.png; a verdict headed with another piece's slug, a
verdict file another piece already used, and a page another piece was graded on are refused.

Diversity scales with memory (.atelier/history.jsonl in the project):
  - every value on every axis is weighted by 1 / (1 + recent uses) ** alpha, alpha = 1 + log2(1 + n/10);
  - a new genome must differ from each of the last 10 on at least d_min axes, d_min = 2 + floor(log2(1 + n/4));
  - empty cells of (register x operator family x ground) are preferred (a quality-diversity archive, after
    MAP-Elites, Mouret and Clune 2015);
  - a topic seen before excludes the operators, lenses, formats and directions already used for it, so the same
    prompt twice never gets the same deal. Standard library only.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import random
import re
import secrets
import shutil
import subprocess
import sys
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
SELF = pathlib.Path(__file__).resolve()
SKILL = SELF.parent.parent
SCRIPTS = SELF.parent
DATA = SKILL / "data"
TASTE = SKILL / "vendor" / "taste-skill" / "library"


def project_home(start=None):
    """The project's .atelier folder: the nearest one in the current folder or above it (as git finds .git), so every command also works
    from a page's own folder; with none, ./.atelier, which new creates."""
    here = pathlib.Path(start or pathlib.Path.cwd()).resolve()
    return next((d / ".atelier" for d in (here, *here.parents) if (d / ".atelier").is_dir()), here / ".atelier")


HOME = project_home()
PIECES = HOME / "pieces"
HISTORY = HOME / "history.jsonl"
STAGES = ["atoms", "lenses", "angles", "genome", "sections", "copy", "visual", "final"]
HOST_STAGES = ["sections", "copy", "visual", "final"]   # --scope design: these belong to the host system's own gates
QUICK_SKIP = ["lenses", "sections", "copy", "final"]      # --scope quick walks the other four: atoms, angles, genome, visual
DONE = ("passed", "host", "skipped")
STOP = set("the a an and or of to in on for with from by at is are was were be this that these those it its our your their into over under about".split())
SIZES = {"slide": (1920, 1080)}   # every other medium renders at the tokens.css default, 1080x1350
COMPOSED = ("image", "carousel")   # media whose pages scaffold composes on the grid from the layout words, in the direction's grammar, instead of copying its specimen
WORD_BUDGET, HOOK_WORDS = 45, 8   # words on one page, every word counted, and in the hook (references/copy.md "Word budget"); render.mjs --audit warns above 45
FONTS = SKILL / "assets" / "fonts"
SPECS = SKILL / "assets" / "directions"
SLUG = re.compile(r"[a-z0-9]([a-z0-9._-]{0,62}[a-z0-9_-])?")   # 1 to 64 characters, no trailing dot
RESERVED = re.compile(r"(con|prn|aux|nul|com\d|lpt\d)(\..*)?")   # Windows device names cannot be folders


def pp(p):
    """A path for printing: forward slashes. Git Bash (Claude Code's Bash tool on Windows) eats backslashes, and Python, node, PowerShell and cmd all read C:/dir/file."""
    return pathlib.PurePath(p).as_posix()


def q(p):
    """A path for a command line: forward slashes, always quoted, so PowerShell, cmd and bash read it the same."""
    return f'"{pp(p)}"'


# The Python that runs compose.py: printed commands use it, since macOS and Linux often have python3 and no python. To PowerShell a line
# that starts with a quoted path is an expression (Windows PowerShell 5.1: "Unexpected token"), so on Windows the line starts with the call
# operator "& ", the form PowerShell runs. Git Bash and MSYS2 set MSYSTEM and take the bash form, the quoted path alone, as macOS and Linux do.
PY = ("& " if sys.platform == "win32" and not os.environ.get("MSYSTEM") else "") + q(sys.executable)


def me(*args):
    """A compose.py command line that works from any folder: the absolute path, quoted."""
    return " ".join([PY, q(SELF), *args])


def tool(name):
    return q(SCRIPTS / name)


def palette_cmd(g, brand=None):
    """The palette.py line for a genome. field_page is the page the layout rhythm gives the colour field; brand is the person's tokens.css."""
    fp = g.get("field_page")
    return (f"{PY} {tool('palette.py')} --register {g['register']} --harmony {g['harmony']} --arc {g['arc']} --pages {len(g['layout_rhythm'])} --ground {g['ground']}"
            + (f" --field-page {fp}" if isinstance(fp, int) else "") + (f" --brand {q(brand)}" if brand else ""))


def check_slug(slug):
    if not SLUG.fullmatch(slug) or RESERVED.fullmatch(slug):
        sys.exit(f"slug '{slug}': use 1 to 64 lower-case letters, digits, '.', '_' or '-', starting with a letter or digit and not ending in '.' (for example q1 or approval-pages). It becomes a folder name.")


def local_types():
    """Ids of the type pairings whose three families all load from the skill's own fonts (fonts-local.css and library/library.css): no download."""
    have = set()
    for css in (FONTS / "fonts-local.css", FONTS / "library" / "library.css"):
        have |= set(re.findall(r"font-family:\s*'([^']+)'", css.read_text(encoding="utf-8"))) if css.is_file() else set()
    return {p["id"] for p in load("type_pairings") if p.get("source") == "local" and {p["display"], p["text"], p["mono"]} <= have}


def type_families(tid):
    """(display, text, mono, local) of a dealt type id. A taste:* id has no mono face and needs get_font.py."""
    p = next((p for p in load("type_pairings") if p["id"] == tid), None)
    if p:
        return p["display"], p["text"], p["mono"], True
    t = next((t for t in taste("type") if f"taste:{t['id']}" == tid), None)
    return (t["display"]["family"], t["text"]["family"], None, False) if t else (None, None, None, False)


def serif_display(tid):
    """True when a dealt type id sets its display face in a serif: a pairing marked "serif" in data/type_pairings.json, or a taste-skill type whose class says serif."""
    p = next((p for p in load("type_pairings") if p["id"] == tid), None)
    return bool(p.get("serif")) if p else any(f"taste:{t['id']}" == tid and "serif" in t.get("class", "") for t in taste("type"))


def specimen(direction, med):
    """The specimen page scaffold starts a direction from, or None. The specimens are 1080x1350 pages, so a slide never starts from one; a film looks for the .motion.html first."""
    names = ([f"{direction}.motion.html"] if med == "video" else []) + [f"{direction}.html"]
    return None if med == "slide" else next((SPECS / n for n in names if (SPECS / n).is_file()), None)


def register_grounds(reg):
    """The grounds a register's colour recipe allows (data/colour.json recipe "ground": dark, paper, mid = a colour field). No ground, or "any", allows all three."""
    text = load("colour")["recipes"].get(load("registers")[reg]["colour"]["recipe"], {}).get("ground", "")
    return {k for k, w in (("dark", "dark"), ("paper", "paper"), ("field", "mid")) if w in text} or {"dark", "paper", "field"}


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def taste(name):
    p = TASTE / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def history():
    if not HISTORY.exists():
        return []
    return [json.loads(l) for l in HISTORY.read_text(encoding="utf-8").splitlines() if l.strip()]


def topic_key(t):
    return {w for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) > 3 and w not in STOP}


def jaccard(a, b):
    return len(a & b) / max(1, len(a | b))


def trigrams(text):
    w = re.findall(r"[a-z0-9']+", text.lower())
    return {tuple(w[i:i + 3]) for i in range(len(w) - 2)} or {tuple(w)}


def piece_path(slug):
    return PIECES / slug / "piece.json"


def load_piece(slug):
    p = piece_path(slug)
    if not p.exists():
        sys.exit(f"no piece '{slug}': run compose.py new {slug} --topic \"...\"")
    return json.loads(p.read_text(encoding="utf-8"))


def save_piece(piece):
    p = piece_path(piece["slug"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(piece, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def rng_for(piece, stage, seed=None):
    if seed is None:
        seed = int.from_bytes(secrets.token_bytes(8), "big")
    piece.setdefault("seeds", {}).setdefault(stage, []).append(seed)
    return random.Random(seed)


def same_topic_runs(piece, hist):
    key = set(piece["topic_key"])
    return [h for h in hist if jaccard(key, set(h.get("topic_key", []))) >= 0.5]


def used(hist, axis, last=20):
    vals = [h.get("genome", {}).get(axis) for h in hist[-last:]]
    return {v: vals.count(v) for v in set(vals) if v}


def alpha(n):
    return 1 + math.log2(1 + n / 10)


def weighted_pick(rng, items, weight, k=1, exclude=()):
    pool = [i for i in items if i not in exclude]
    out = []
    for _ in range(min(k, len(pool))):
        ws = [max(1e-6, weight(i)) for i in pool]
        r, acc = rng.random() * sum(ws), 0.0
        for item, w in zip(pool, ws):
            acc += w
            if acc >= r:
                out.append(item)
                pool.remove(item)
                break
    return out


ATOM_ROW = re.compile(r"^\|\s*\d+\s*\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|", re.M)
MADE_UP = re.compile(r"no source|made[ -]up|invented|sample|^\s*(?:none|n/?a|-+)?\s*$", re.I)


def atoms_of(piece):
    """The filled rows of the piece's 01-atoms.md: each atom's types, whether it has a real source, and whether that source is the person's
    own record ('first-party: <file>'). An empty list when the table has no filled row (design scope adopts its angle and has none)."""
    f = PIECES / piece["slug"] / "01-atoms.md"
    rows = ATOM_ROW.findall(f.read_text(encoding="utf-8")) if f.is_file() else []
    return [{"types": set(re.findall(r"[a-z-]+", typ.lower())), "sourced": not MADE_UP.search(src), "first_party": not MADE_UP.search(src) and bool(re.search(r"first[ -]party", src, re.I))}
            for typ, atom, src in rows if atom.strip()]


def needs_text(nd):
    """What a hook or close needs from the atoms, in words."""
    return ("a first-party atom (your own record, source 'first-party: <file>')" if nd.get("first_party") else
            f"a sourced {' or '.join(nd.get('types', []))} atom")


def supported(item, atoms):
    """True when the atoms can carry a hook or close honestly: it needs nothing, or a sourced atom of the kind it needs is there."""
    nd = item.get("needs")
    if not nd:
        return True
    return any(a["sourced"] and (not nd.get("first_party") or a["first_party"]) and (not nd.get("types") or a["types"] & set(nd["types"])) for a in atoms)


def grammar(did):
    """A direction's borrowed form and grammar: its row in references/directions.md."""
    for line in (SKILL / "references" / "directions.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] == did:
            return cells[1]
    return ""


def compose_brief(piece):
    """What the builder composes, before any page exists: the direction's grammar and the specimen frame to leave, each page's layout word,
    the object, and the word budget. Empty before the genome is dealt."""
    g = piece.get("genome")
    if not g:
        return ""
    med, did = piece["medium"], g["direction"]
    d = next((x for x in load("directions") if x["id"] == did), {})
    layouts = load("structures").get("layouts", {})
    objs = [str(i) for i, a in enumerate(atoms_of(piece), 1) if a["sourced"] and "object" in a["types"]]
    spec = specimen(did, med)
    lines = [f'Compose the page{"s" if len(g["layout_rhythm"]) > 1 else ""}. ' + ("Scaffold gives the grid, the dealt type and the colour roles, each page set up for its layout word; it does not copy the specimen." if spec and med in COMPOSED else "Build it from the direction's grammar and the layout words below."),
             f'- Direction "{did}": {grammar(did)}']
    if spec and med in COMPOSED and d.get("frame"):
        lines.append(f'  Its specimen ({pp(spec)}; picture {pp(SPECS / "specimens" / (did + ".png"))}) shows the grammar\'s rules. Its frame is: {d["frame"]}. '
                     "Do not compose the page in that frame: the art-director judges distinct against this specimen.")
    if d.get("stock"):
        lines.append("- Stock parts of the specimen, which must not appear unchanged on the page: " + "; ".join(d["stock"]) + ". "
                     "Critics read these parts as the specimen itself. Turn each into a form the object has, or leave it out.")
    lines += [f'- Page {i} layout "{w}": {layouts.get(w, "")}' for i, w in enumerate(g["layout_rhythm"], 1)]
    lines.append("- The object: " + (f"atom {', '.join(objs)} (typed object) is the thing only this topic has" if objs else "no sourced atom is typed object: take the one thing only this topic has from the sourced atoms")
                 + ". Build the direction's device out of it: the direction lends its rules (what a ledger adds up, what a map connects), and the drawing is the object itself, "
                 "with its own count, shape, labels and order. Before you build, write one line: \"On this page, <the object> becomes <the direction's device>, "
                 "drawn as <the object's own form>, not as <the stock part it replaces>.\"")
    lines.append(f'- Word budget: {WORD_BUDGET} words or fewer on each page, every word counted, the source line too; the hook {HOOK_WORDS} words or fewer. '
                 f'The post text carries the rest (references/copy.md "Word budget"). render.mjs --audit warns above {WORD_BUDGET}: cut before any critic sees the page.')
    return "\n".join(lines)


def worksheet(piece, stage, body):
    f = PIECES / piece["slug"] / f"{STAGES.index(stage) + 1:02d}-{stage}.md"
    f.write_text(body, encoding="utf-8")
    return f


# ---------- stage worksheets ----------

def needs_critic(piece, stage):
    """Independent stages carry a critic's verdict file. In quick scope the one angle may be graded by its author; the visual is the stage someone else checks."""
    return load("rubrics")["stages"][stage]["independent"] and not (piece.get("scope") == "quick" and stage == "angles")


def grade_cmd(piece, stage):
    """The exact grade command for one stage, with placeholders for the two files."""
    rub = load("rubrics")["stages"][stage]
    cmd = me("grade", piece["slug"], stage, '--scores "' + ",".join(f"{c['id']}=" for c in rub["criteria"]) + '"', "--notes <notes.md>", "--by " + ("critic" if needs_critic(piece, stage) else "self"))
    if needs_critic(piece, stage):
        cmd += " --evidence <critic-verdict.md>"
    if any("swap_test" in c["if"] for c in rub.get("caps", [])):
        cmd += " --swap <pass-or-fail>"
    return cmd


def grade_block(piece, stage):
    """The grade command and a notes template for one stage, so the exact formats are never learned from an error."""
    rub = load("rubrics")["stages"][stage]
    crit, ind = rub["criteria"], needs_critic(piece, stage)
    lines = "\n".join(f"{c['id']}: " for c in crit)
    quick = piece.get("scope") == "quick"
    anchors = "".join(f'  {c["id"]} anchors for a {"quick" if quick else "full"} piece: ' + "; ".join(f"{k} = {v}" for k, v in c["anchors_quick" if quick else "anchors"].items()) + "\n"
                      for c in crit if "anchors_quick" in c)
    return (f'Grade (rubric: data/rubrics.json "{stage}"):\n  {grade_cmd(piece, stage)}\n{anchors}'
            + ("  --evidence is the critic agent's verdict file: 200 characters or more, a verdict line (verdict: PASS or FAIL) or a score line, and not your notes file. A FAIL or REVISE verdict cannot pass the stage. Scores or a total in the file must be the numbers you type in --scores.\n" if ind else "")
            + (f"  The visual stage also needs a fresh render: audit.json saying PASS and page-NN.png, each newer than the page's HTML. They are looked for next to the scaffolded page; for a page built without scaffold, add --folder DIR. The critic's file is headed with this piece's slug ('## {piece['slug']}') and is used for this piece only.\n" if stage == "visual" else "")
            + f'The notes file has one line per criterion, "criterion: reason". Each reason is 25 or more characters and quotes or locates the evidence:\n```\n{lines}\n```\n')


def ws_atoms(piece):
    return worksheet(piece, "atoms", f"""# Stage 1: atoms (decompose before you create)
Topic: {piece['topic']}

Break the topic into {"3 to 5" if piece.get("scope") == "quick" else "8 to 12"} atoms, one per line, each typed and sourced. Digest them one at a time: for each,
write what it is, why it matters, and the one detail that makes it specific. No prose, no angle yet.

| # | type | atom (concrete: a number, object, role, time, place) | source (a URL or a published work; "first-party: <file>" for your own record; "no source" for a made-up object, labelled on the page) | why it matters |
|---|---|---|---|---|
| 1 | fact / number / object / quote / role / place / time / tension / mechanism / myth / limit / metaphor-seed | | | |

The genome deal reads this table. A hook or close that needs material is dealt only when a sourced atom carries it: a confession and the closes "changed" and "next-test" need a first-party atom, a moment a time atom (a real dated instant), a quote a quote atom, an artefact an object atom, a number or price hook a number atom.

{grade_block(piece, 'atoms')}""")


def deal_lenses(piece, seed):
    hist = history()
    rng = rng_for(piece, "lenses", seed)
    lenses = load("lenses")
    prior = {l for h in same_topic_runs(piece, hist) for l in h.get("lenses", [])}
    tried = {l for att in piece["stages"]["lenses"].get("deals", []) for l in att}
    a, u = alpha(len(hist)), {}
    for h in hist[-20:]:
        for l in h.get("lenses", []):
            u[l] = u.get(l, 0) + 1
    ids = [l["id"] for l in lenses]
    pick = weighted_pick(rng, ids, lambda i: 1 / (1 + u.get(i, 0)) ** a, k=3, exclude=prior | tried)
    if len(pick) < 3:
        pick += weighted_pick(rng, ids, lambda i: 1.0, k=3 - len(pick), exclude=set(pick))
    piece["stages"]["lenses"].setdefault("deals", []).append(pick)
    rows = "\n".join(f"- **{l['name']}** ({l['id']}): {l['question']}" for l in lenses if l["id"] in pick)
    return worksheet(piece, "lenses", f"""# Stage 2: lenses (three ways of seeing, dealt)
Topic: {piece['topic']}

{rows}

For each lens, write two lines: what this viewer notices in the atoms, and the one atom they would point at.
{grade_block(piece, 'lenses')}""")


def deal_angles(piece, seed):
    hist = history()
    rng = rng_for(piece, "angles", seed)
    ops = [o for o in load("operators") if piece["medium"] in o["fits"]]
    prior = {o for h in same_topic_runs(piece, hist) for o in h.get("operators", [])}
    tried = {o for att in piece["stages"]["angles"].get("deals", []) for o in att}
    a, u = alpha(len(hist)), {}
    for h in hist[-20:]:
        for o in h.get("operators", []):
            u[o] = u.get(o, 0) + 1
    fam_seen = {}
    for h in hist[-10:]:
        f = h.get("genome", {}).get("operator_family")
        fam_seen[f] = fam_seen.get(f, 0) + 1
    by_id = {o["id"]: o for o in ops}
    pick = weighted_pick(rng, list(by_id), lambda i: (1 / (1 + u.get(i, 0)) ** a) / (1 + fam_seen.get(by_id[i]["family"], 0)), k=3 if piece.get("scope") == "quick" else 6, exclude=prior | tried)
    # at most two operators from one family in a deal, so the candidates differ in kind
    fams, kept = {}, []
    for i in pick:
        f = by_id[i]["family"]
        if fams.get(f, 0) < 2:
            kept.append(i)
            fams[f] = fams.get(f, 0) + 1
    lens = piece["stages"]["lenses"].get("deals", [[]])[-1]
    quick = piece.get("scope") == "quick"
    piece["stages"]["angles"].setdefault("deals", []).append(kept)
    rows = "\n".join(f"{n}. **{by_id[i]['name']}** ({i}, {by_id[i]['family']}): {by_id[i]['recipe']}  \n   e.g. {by_id[i]['example']}  \n   risk: {by_id[i]['risk']}"
                     + ("" if quick else f"  \n   lens to use: {lens[(n - 1) % len(lens)] if lens else 'any'}") for n, i in enumerate(kept, 1))
    if quick:
        how = f"""Quick scope: {len(kept)} operators are dealt below. Pick the ONE that fits the atoms best and write ONE angle with it, not one per operator:
a one-line idea, the atoms it uses, the gap it opens (tension), and why only we could say it (swap test).
Check it for novelty against everything made before:
  {me('similar', piece['slug'], '"<one-line>"')}
You grade this stage yourself, so be harsh. A critic checks the visual."""
        record = "Then record the operator you used (its number below) with your one line:\n  " + me("choose", piece["slug"], "angle", "<n>", '--text "<your one line>"')
    else:
        how = f"""Full scope: {len(kept)} operators are dealt below. Write ONE candidate angle for EACH of them, through the lens named:
a one-line idea, the atoms it uses, the gap it opens (tension), and why only we could say it (swap test).
Then check each one-line for novelty against everything made before:
  {me('similar', piece['slug'], '"<one-line>"')}
Then have the story-editor agent grade the candidates and write its verdict to a file (one entry per candidate); the best total is the stage grade."""
        record = "Then record the winner:\n  " + me("choose", piece["slug"], "angle", "<n>", '--text "<its one line>"')
    return worksheet(piece, "angles", f"""# Stage 3: angles (intelligent play, dealt)
Topic: {piece['topic']}

{how}
{grade_block(piece, 'angles')}{record}

{rows}
""")


def genome_axes(med):
    formats = [f for f in load("formats") if f["medium"] == med]
    dirs = [d for d in load("directions") if med in d["media"]]
    colour = load("colour")
    st = load("structures")
    return {
        "format": [f["id"] for f in formats],
        "direction": [d["id"] for d in dirs],
        "register": list(load("registers")),
        "hook": [h["id"] for h in st["hooks"]],
        "close": [c["id"] for c in st["closes"]],
        "harmony": [h["id"] for h in colour["harmonies"]],
        "arc": [x["id"] for x in colour["arcs"]] if med in {"carousel", "video", "slide"} else ["steady"],
        "type": [p["id"] for p in load("type_pairings")] + [f"taste:{t['id']}" for t in taste("type")],
        "motion": [f"taste:{m['id']}" for m in taste("motions")] if med == "video" else ["none"],
    }


def layout_rhythm(rng, words, k, lead=None, avoid=None):
    """One layout word per section, never the same twice in a row. A format's lead layout is pinned to its page and used on no other page; the colour field comes at most once.
    avoid: the layout of the dealt direction's specimen, never dealt to page 1 (unless the format pins it there), so the cover is not composed like the specimen."""
    pin = {lead["page"] - 1: lead["layout"]} if lead and lead["page"] <= k else {}
    out = []
    for i in range(k):
        ban = set(pin.values()) | set(out[-1:]) | ({"field"} if "field" in out else set()) | ({avoid} if i == 0 and avoid else set())
        out.append(pin[i] if i in pin else rng.choice([x for x in words if x not in ban]))
    return out


def deal_genome(piece, seed, any_type=False):
    hist = history()
    rng = rng_for(piece, "genome", seed)
    n = len(hist)
    a = alpha(n)
    d_min = 2 + int(math.floor(math.log2(1 + n / 4)))
    med = piece["medium"]
    angle = piece.get("angle") or {}
    ops = {o["id"]: o for o in load("operators")}
    formats = [f for f in load("formats") if f["medium"] == med]
    dirs = [d for d in load("directions") if med in d["media"]]
    st = load("structures")
    prior_topic = same_topic_runs(piece, hist)
    banned = {ax: {h.get("genome", {}).get(ax) for h in prior_topic} for ax in ("format", "direction", "operator")}
    recent = hist[-10:]
    axes = genome_axes(med)
    if not any_type:   # type is dealt only from pairings whose fonts ship with the skill; --any-type adds taste-skill's, which need get_font.py
        axes["type"] = [t for t in axes["type"] if t in local_types()]
    pins = piece.get("pins", {})   # design scope: axes the host system has already decided (its own direction rotation, the post's register)
    for ax, v in pins.items():
        axes[ax] = [v]
        banned.get(ax, set()).discard(v)
    regs = load("registers")
    overuse = {f["id"]: f["overuse"] for f in formats}
    ground_of = {d["id"]: d["ground"] for d in dirs}
    spec_lay = {d["id"]: d.get("layout") for d in dirs}   # the layout of each direction's specimen page, kept off page 1
    cells = {}
    for h in hist:
        g = h.get("genome", {})
        c = (g.get("register"), g.get("operator_family"), g.get("ground"))
        cells[c] = cells.get(c, 0) + 1

    def w(axis, v):
        base = 1 / (1 + used(hist, axis).get(v, 0)) ** a
        if axis == "format":
            base *= 1 - 0.6 * overuse.get(v, 0)
        if v in banned.get(axis, set()):
            base *= 0.0
        return base

    def pick(ax, vals):
        return weighted_pick(rng, vals, lambda v: w(ax, v))[0] if any(w(ax, v) > 0 for v in vals) else rng.choice(vals)

    def only(vals, keep):   # a filter that never empties a list: a host's pin stays, even against the register
        return [v for v in vals if keep(v)] or vals

    atoms = atoms_of(piece)
    left_out = []
    if atoms:   # never deal a hook or close the atoms cannot support honestly (an admission, a dated instant or a quote would have to be invented)
        for ax, key in (("hook", "hooks"), ("close", "closes")):
            if ax not in pins:
                left_out += [(ax, x["id"], needs_text(x["needs"])) for x in st[key] if x["id"] in axes[ax] and not supported(x, atoms)]
                axes[ax] = only(axes[ax], lambda v, key=key: supported(next(x for x in st[key] if x["id"] == v), atoms))
    quick = piece.get("scope") == "quick"
    if quick:   # one image starts from a specimen page: deal only a direction that has one (full and design scope scaffold a plain page for the others)
        axes["direction"] = only(axes["direction"], lambda d: specimen(d, med))
    serifs = {t for t in axes["type"] if serif_display(t)}
    # the register comes first: its colour recipe limits the ground (so the direction), and its type voice limits the pairing
    grounds = {r: register_grounds(r) for r in regs}
    keeps_house = {d["id"] for d in dirs if d.get("keeps_house_type")}
    regs_ok = only(axes["register"], lambda r: any(ground_of[d] in grounds[r] for d in axes["direction"]))
    best, best_score = None, -1.0
    for _ in range(400):
        g = {"register": pick("register", regs_ok)}
        g["direction"] = pick("direction", only(axes["direction"], lambda d: ground_of[d] in grounds[g["register"]]))
        suit = regs[g["register"]].get("pairings")
        bare_paper = not piece.get("brand") and ground_of.get(g["direction"], "paper") == "paper"   # no --brand: palette.py makes the piece's own palette, and a serif display on a warm paper ground risks cluster 1 (warm cream plus a serif)
        for ax, vals in axes.items():
            if ax not in g:
                if ax == "type":
                    vals = only(vals, lambda t: t in suit or t.startswith("taste:")) if suit else vals
                    vals = only(vals, lambda t: t not in serifs) if bare_paper else vals
                g[ax] = pick(ax, vals)
        if g["direction"] in keeps_house and "type" not in pins:
            g["type"] = "house"   # the direction's whole idea is the house type's width axis
        g["operator"] = angle.get("operator", "")
        g["operator_family"] = ops.get(g["operator"], {}).get("family", "")
        g["lens"] = angle.get("lens", "")
        g["ground"] = ground_of.get(g["direction"], "paper")
        gf = next((f for f in formats if f["id"] == g["format"]), {})
        g["layout_rhythm"] = layout_rhythm(rng, st["layout_words"], len(gf.get("sections", [1] * 5)), gf.get("lead"), spec_lay.get(g["direction"]) if med in COMPOSED else None)
        g["field_page"] = g["layout_rhythm"].index("field") + 1 if "field" in g["layout_rhythm"] else "none"
        dists = [sum(1 for ax in axes if g.get(ax) != h.get("genome", {}).get(ax)) for h in recent]
        if dists and min(dists) < min(d_min, len(axes) - 1):
            continue
        novelty = (sum(dists) / len(dists) / len(axes)) if dists else 1.0
        cell = 1 / (1 + cells.get((g["register"], g["operator_family"], g["ground"]), 0)) ** a
        score = novelty + cell + 0.05 * rng.random()
        if score > best_score:
            best, best_score = g, score
    if best is None:
        sys.exit("no genome satisfies the diversity rules: widen the medium or add vocabulary to data/")
    piece["genome"] = best
    piece["stages"]["genome"].setdefault("deals", []).append(best)
    if (PIECES / piece["slug"] / "07-visual.md").is_file():   # the visual worksheet now names the dealt direction, layouts, object and word budget
        ws_generic(piece, "visual")
    rec = load("registers")[best["register"]]
    fmt = next(f for f in formats if f["id"] == best["format"])
    lines = "\n".join(f"- {k}: {v}" for k, v in dict(best, lens=best["lens"] or ("none (quick scope)" if quick else "(host angle)")).items())
    define = lambda k: next((x["definition"] + (f" It needs {needs_text(x['needs'])}." if x.get("needs") else "") for x in st[k + "s"] if x["id"] == best[k]), "")
    honest = (("Left out of this deal, because no sourced atom carries them: " + "; ".join(f"{ax} {i} (needs {w})" for ax, i, w in left_out) + ". " if left_out else "")
              + ("Never invent an admission, a date, a quote or a record to fit the hook or the close: re-deal instead." if atoms else
                 "The hook and close were dealt without an atoms table: if the material cannot carry them honestly (a confession needs your own record, a moment a real dated instant, a quote a real line), re-deal."))
    lead = fmt.get("lead")
    disp, text, mono, local = type_families(best["type"])
    face = f"display {disp}, text {text}" + (f", mono {mono}" if mono else "")
    return worksheet(piece, "genome", f"""# Stage 4: genome (the dealt design of this piece)
Diversity rules applied: {n} pieces in memory, alpha {a:.2f}, every genome at least {d_min} axes from each of the last 10.{f" Pinned{' by the host' if piece.get('scope') == 'design' else ' with --pin'}: {', '.join(f'{k}={v}' for k, v in pins.items())}." if pins else ""}
Register filters: ground and direction follow the colour recipe (it allows {', '.join(sorted(grounds[best['register']]))}), type follows the register's voice, and type comes {'from any pairing (--any-type)' if any_type else 'only from the local font library'}; a pin from the host overrides a filter.

{lines}

Format "{fmt['name']}": sections {fmt['sections']}{f'. The format pins its lead layout: page {lead["page"]} is "{lead["layout"]}".' if lead else ""}
Hook "{best['hook']}": {define('hook')}
Close "{best['close']}": {define('close')}
{honest}
Register "{best['register']}": {rec['feeling']}. Colour: {rec['colour']}. Motion: {rec['motion']}. Type: {rec['type']}. Words: {rec['words']}.
Colour: run this in the folder where the page will live. It writes palette.css and colour-plan.md there. Run it before scaffold, which links palette.css when it exists:
  {palette_cmd(best, piece.get("brand"))}
  Apply it as references/colour.md "Applying it" says.{"" if piece.get("brand") else " With no --brand it makes this piece's own palette from the register, harmony and arc, kept off the specimens' colours; pass your own tokens.css with new --brand."}
Type: "{best['type']}": {face}. {'Local: scaffold links the font library and sets --disp, --body and --mono to it (a face your --brand file declares is kept).' if local else 'Not local: run get_font.py for these families before the page can load them.'}
Layout rhythm, one word per section: {' > '.join(best['layout_rhythm'])}. Field page: {best['field_page']} (the colour field comes on that page and the palette follows).{f" Page 1 is never laid out as the specimen's own layout, {spec_lay[best['direction']]}." if med in COMPOSED and spec_lay.get(best['direction']) else ""}

{compose_brief(piece)}

Check the genome serves the angle; if one axis fights it, re-deal (a fresh deal excludes this one).
{grade_block(piece, 'genome')}""")


def ws_generic(piece, stage):
    guide = {
        "sections": "Break the piece into its sections (one per page, beat or paragraph), following the genome's format and layout rhythm. Write each section as: job (claim, proof, turn or payoff), the one atom it uses, the words, the visual. Digest them one at a time. Then have the story-editor grade the set.",
        "copy": f"Write the final words for every section and the caption. Run {PY} {tool('copy_lint.py')} <file> on them, then the copy-critic agent.",
        "visual": f"Start the page: {me('scaffold', piece['slug'])} (working links, the dealt type and colours; for an image or a carousel a composition start on the grid, not the direction's specimen; run the palette line from the genome worksheet first and scaffold links palette.css). Write the post text that goes out with the page (post.md next to it): every claim, number and quote on the page is in it, because the critic checks the page against it. Build the pages from the genome's direction, palette.css and type pairing, then run: node {tool('render.mjs')} visual.html --audit (fix every FAIL, and every phone read, claim twice, wrapped run, hairline accent, empty cell, faint mark and thin stroke warning, before the art-director sees the page) ; {PY} {tool('attention.py')} <folder> ; {PY} {tool('cvd.py')} <folder> ; {PY} {tool('layout_memory.py')} check <cover.png> ; {PY} {tool('video_check.py')} <folder> for motion. If Python Playwright is installed, also run huashu-design's checker for template habits and look families: {PY} {q(SKILL / 'vendor' / 'huashu-design' / 'scripts' / 'design_lint.py')} check <file.html> --viewport 1080x1350 --min-body 22 --min-label 22, then the same script with ledger check <file.html> (it warns when the look repeats a recent piece). Give the renders, the post text and all script output to the art-director agent.",
        "final": "Look at the whole piece as a stranger, on a phone. Have the art-director and the story-editor grade it together.",
    }[stage]
    brief = compose_brief(piece) if stage == "visual" else ""
    return worksheet(piece, stage, f"# Stage {STAGES.index(stage) + 1}: {stage}\n\n{guide}\n\n" + (brief + "\n\n" if brief else "") + grade_block(piece, stage))


# ---------- grading ----------

def check_cap(cond, scores, swap):
    m = re.match(r"(\w+)\s*(<=|<|==)\s*(\w+)", cond)
    if not m:
        return False
    k, op, v = m.groups()
    if k == "swap_test":
        return swap == v
    x = scores.get(k)
    if x is None:
        return False
    v = float(v)
    return x < v if op == "<" else x <= v if op == "<=" else x == v


# a verdict line is labelled "verdict" or "<stage> verdict" ("verdict: PASS", "visual verdict: fail"), in any case. No other label counts: the
# art-director's 'seen: "FAILED: 3 of 12 nightly jobs"' quotes the page, and a bare PASS or FAIL somewhere in the text is not a verdict either.
VERDICT = re.compile(r"^[^A-Za-z0-9\n]*(?:[A-Za-z][\w-]*[ \t]+)?(?i:verdict)[ \t]*[:=][^A-Za-z0-9\n]*(?P<word>[A-Za-z]+)(?P<rest>[^\n]*)", re.M)
WORDS = {"PASS": "PASS", "PASSED": "PASS", "FAIL": "FAIL", "FAILED": "FAIL", "REJECT": "FAIL", "REJECTED": "FAIL", "REVISE": "REVISE"}
SCORE_LINE = re.compile(r"^[^A-Za-z0-9\n]*(?i:scores?|total|winner)\b[^\n]*[:=]|\b\d+(?:\.\d+)?\s*(?:/|of)\s*(?:10|40)\b", re.M)


def verdicts(text):
    """Every verdict the text states, as PASS, FAIL or REVISE. A line that offers a choice ("PASS | FAIL", "PASS or FAIL") states none."""
    out = []
    for m in VERDICT.finditer(text):
        v = WORDS.get(m["word"].upper())
        if v and not re.match(r"\s*(?:[|/]|or\b)\s*(?:PASS|FAIL|REVISE)", m["rest"], re.I):
            out.append(v)
    return out


def critic_read(text, ids):
    """What a critic's text states: its worst verdict, the lowest score it gives each criterion in ids, and its lowest total.
    Scores are read from a 'scores:' line ("idea 8, hook 7" or "idea=8") or a line that starts with the criterion ("idea: 8/10")."""
    vs, sc, tot = verdicts(text), {}, []
    for line in text.splitlines():
        m = re.match(r"[\W_]*(?i:scores?)\s*[:=](.*)", line)
        for c in ids:
            x = (re.search(rf"(?<![\w-]){re.escape(c)}(?![\w-])\s*[:=]?\s*(\d+(?:\.\d+)?)", m.group(1)) if m
                 else re.match(rf"[\W_]*{re.escape(c)}\s*[:=]\s*(\d+(?:\.\d+)?)", line, re.I))
            if x and 1 <= float(x.group(1)) <= 10:
                sc[c] = min(sc.get(c, 10.0), float(x.group(1)))
        t = re.search(r"\btotal\b\s*[:=]?\s*(\d+(?:\.\d+)?)", line, re.I) or re.search(r"\b(?i:scores?|overall|grade)\s*[:=]\s*(\d+(?:\.\d+)?)\s*(?:/|of)\s*10\b", line)
        if t and 1 <= float(t.group(1)) <= 10:
            tot.append(float(t.group(1)))
    return {"verdict": next((v for v in ("FAIL", "REVISE", "PASS") if v in vs), None), "scores": sc, "total": min(tot) if tot else None}


def best_entry(text, ids):
    """A file that grades several candidates has one '## ' entry each: the entry with the best total stands for the stage."""
    parts = re.split(r"(?m)^#{2,3}[ \t]", text)
    if len(parts) < 3:
        return critic_read(text, ids)
    best = max((critic_read(p, ids) for p in parts[1:]), key=lambda r: (r["total"] or 0, r["verdict"] == "PASS"))
    head = critic_read(parts[0], ids)["verdict"]   # an overall verdict above the entries
    return dict(best, verdict=head) if head in ("FAIL", "REVISE") else best


def says(text, phrase, n=6):
    """True when n or more consecutive words of phrase appear in a row in text."""
    p, t = re.findall(r"[a-z0-9']+", phrase.lower()), " " + " ".join(re.findall(r"[a-z0-9']+", text.lower())) + " "
    n = min(n, len(p))
    return n > 0 and any(" " + " ".join(p[i:i + n]) + " " in t for i in range(len(p) - n + 1))


def other_pieces(slug):
    """(slug, evidence records) of every other piece in this project, from the piece.json files and history.jsonl: what each piece's grades rest on."""
    out = []
    for f in sorted(PIECES.glob("*/piece.json")):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        out.append((p.get("slug"), [g.get("evidence", {}) for st in p.get("stages", {}).values() for g in st.get("grades", [])] + [{"sha256": p.get("angle", {}).get("evidence_sha256")}]))
    out += [(h.get("slug"), list(h.get("evidence", {}).values())) for h in history()]
    return [(s, evs) for s, evs in out if s and s != slug]


def used_by(slug, sha):
    """The other piece whose grades already rest on this sha256 (a critic's verdict file or a rendered page), or None."""
    return next((s for s, evs in other_pieces(slug) for e in evs if sha in (e.get("sha256"), e.get("render", {}).get("html_sha256"))), None)


def check_evidence(path, what, notes=None, angle=None, ids=(), best=False, slug=None):
    """A grade is only as good as the file behind it. The file must exist, hold 200 characters or more, differ from the author's
    notes, and carry a verdict line or a score line; to adopt an angle it must also name that angle or carry a winner or PASS line,
    and a record whose only verdict is FAIL or REVISE is refused. With ids (a stage's criteria) the record also holds the verdict,
    the per-criterion scores and the total the file states, for cmd_grade to hold the typed scores to. best: the file grades
    candidates, one '## ' entry each. slug: the piece being graded; the file must be its own verdict, not one headed '## <another
    piece>' and not a file another piece already used. Returns the record that goes to memory."""
    ev = pathlib.Path(path) if path else None
    raw = ev.read_bytes() if ev and ev.is_file() else b""
    text = raw.decode("utf-8", errors="replace").strip()
    sha = hashlib.sha256(raw).hexdigest()
    if len(text) < 200:
        sys.exit(f"--evidence must be {what} (a file of 200 characters or more); a grade nobody else wrote cannot count")
    if notes and (ev.resolve() == notes.resolve() or raw == notes.read_bytes()):
        sys.exit(f"--evidence must differ from your notes file: it is {what}, written by the critic, not by the author")
    if slug:
        others, heads = {s for s, _ in other_pieces(slug)}, [h.lower() for h in re.findall(r"(?mi)^#{2,3}[ \t]+\W*([a-z0-9][a-z0-9._-]*)", text)]
        named = next((h for h in heads if h in others), None)
        if named and slug not in heads:
            sys.exit(f"--evidence is headed '## {named}', the name of another piece, and this piece is '{slug}': it is the verdict for that piece. Have the critic judge '{slug}' and head its entry '## {slug}'.")
        twin = used_by(slug, sha)
        if twin:
            sys.exit(f"--evidence is the file that piece '{twin}' already used (the same sha256): every piece needs its own critic verdict. Have the critic judge '{slug}' and write a new file.")
    said = verdicts(text)
    if not (said or SCORE_LINE.search(text)):
        sys.exit(f"--evidence has no verdict or score line (for example 'verdict: PASS' or 'score: 8/10'; a PASS somewhere in the text is not one): it must be {what}")
    if angle is not None:
        if said and "PASS" not in said:
            sys.exit(f"--evidence says {said[0]}: an angle the host did not pass cannot be adopted")
        if not (says(text, angle) or "PASS" in said or re.search(r"^\W*winner\b", text, re.M | re.I)):
            sys.exit("--evidence does not name this angle (6 or more words of it in a row) and has no 'winner' or PASS line: it is not the record for this angle")
    rec = {"path": str(ev.resolve()), "sha256": sha}
    if ids:
        rec.update({k: v for k, v in (best_entry if best else critic_read)(text, ids).items() if v})
    return rec


def render_cmd(html, medium):
    """The audit line; for a film, the same length and poster time as the motion.mjs line scaffold prints, so the audit checks every half second and the poster."""
    size = SIZES.get(medium)
    return f"node {tool('render.mjs')} {q(html)} --audit" + (f" --size {size[0]}x{size[1]}" if size else "") + (" --seconds 8 --poster 7" if medium == "video" else "")


def check_render(piece, folder):
    """The visual stage grades what was rendered: an audit.json that says PASS and a page-NN.png for every audited page (video.mp4 too for a film),
    each newer than the page's HTML. The folder is the one scaffold wrote the page in (--folder may only name that one); a piece with no scaffolded page
    takes --folder, else visual.html in the project folder or the piece's own folder. The page must not be one another piece was graded on.
    Returns the record that goes into the grade: the page and every page-NN.png with their sha256."""
    rec = pathlib.Path(piece["visual_html"]) if piece.get("visual_html") else None
    if rec and folder and pathlib.Path(folder).resolve() != rec.parent:
        sys.exit(f"--folder {pp(folder)} is not the folder scaffold wrote this piece's page into ({pp(rec.parent)}): the grade rests on this piece's own page and render. Leave --folder out. Or scaffold the page into {pp(folder)}, then build and render it there:\n  {me('scaffold', piece['slug'], '--out', q(pathlib.Path(folder) / 'visual.html'), '--force')}")
    cands = [pathlib.Path(folder).resolve()] if folder else [rec.parent] if rec else [pathlib.Path.cwd(), PIECES / piece["slug"]]
    page_in = lambda c: rec if rec and rec.parent == c else c / "visual.html"   # the scaffolded page keeps its own file name
    where = next((c for c in cands if page_in(c).is_file()), None)
    if not where:
        sys.exit(f"the visual stage grades a rendered page, and there is no visual.html in {' or '.join(map(pp, cands))}{'' if rec else '. For a page built without scaffold, give its folder with --folder'}. To scaffold the page, run:\n  {me('scaffold', piece['slug'])}")
    html = page_in(where)
    sha = hashlib.sha256(html.read_bytes()).hexdigest()
    twin = used_by(piece["slug"], sha)
    if twin:
        sys.exit(f"{pp(html)} is the page that piece '{twin}' was already graded on (the same sha256): a piece is graded on its own page. Build this piece's page in a folder of its own, render it, and grade that. To start the page, run:\n  {me('scaffold', piece['slug'], '--out', q(where / piece['slug'] / 'visual.html'))}")
    fix = f"Fix the page if needed, then render it again:\n  {render_cmd(html, piece['medium'])}"
    try:
        pages = json.loads((where / "audit.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        sys.exit(f"no readable audit.json in {pp(where)}. {fix}")
    pages = pages if isinstance(pages, list) else []
    failed = [p for p in pages if p.get("fails")]
    if not pages or failed:
        sys.exit(f"audit.json in {pp(where)} does not say PASS ({len(failed)} of {len(pages)} page(s) have hard fails). {fix}")
    need = [where / "audit.json"] + [where / f"page-{i:02d}.png" for i in range(1, len(pages) + 1)] + ([where / "video.mp4"] if piece["medium"] == "video" else [])
    old = [f.name for f in need if not f.is_file() or f.stat().st_mtime_ns < html.stat().st_mtime_ns]
    if old:
        sys.exit(f"missing, or older than {html.name}: {', '.join(old)}. The grade must be of the page as rendered now. {fix}")
    return {"html": str(html), "html_sha256": sha, "pages": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in need if f.suffix == ".png"}}


def keep_attempt(piece, folder, n, evidence):
    """A copy of visual attempt n: its page, page-NN.png, audit.json and the critic's verdict, in the piece's attempts/visual-<n>, so a later
    attempt can start again from the best one (the 30 Oct 2026 runs went 7.3 then 7.2: each revision rebuilt and added new faults).
    Nothing is copied when the page cannot be found; returns the folder or None."""
    rec = pathlib.Path(piece["visual_html"]) if piece.get("visual_html") else None
    where = pathlib.Path(folder).resolve() if folder else rec.parent if rec else pathlib.Path.cwd()
    page = rec if rec and rec.parent == where else where / "visual.html"
    if not page.is_file():
        return None
    dst = PIECES / piece["slug"] / "attempts" / f"visual-{n}"
    dst.mkdir(parents=True, exist_ok=True)
    for f in [page, where / "audit.json", *sorted(where.glob("page-*.png"))]:
        if f.is_file():
            shutil.copyfile(f, dst / f.name)
    if evidence and pathlib.Path(evidence).is_file():
        shutil.copyfile(evidence, dst / "verdict.md")
    return dst


def revise_from_best(piece, st):
    """The revise step of the visual stage: start again from the best attempt so far, apply only its verdict's fixes, keep what it keeps."""
    gs = st.get("grades", [])
    k = max(range(len(gs)), key=lambda i: (gs[i]["total"], -i))
    g, kept = gs[k], gs[k].get("attempt")
    lines = [f"visual: REVISE (attempt {st['attempts'] + 1}). Start from attempt {k + 1}, the best so far ({g['total']:g})"
             + (f": its page, renders and verdict are kept in {pp(kept)}. If a later attempt scored lower, copy that visual.html back over the page first." if kept else ".")
             + " Apply only that verdict's numbered fixes and keep what it says works. Add nothing else: in the 30 Oct 2026 runs every new element brought a new fault."]
    v = pathlib.Path(kept) / "verdict.md" if kept else pathlib.Path(g.get("evidence", {}).get("path", ""))
    text = v.read_text(encoding="utf-8", errors="replace") if v.is_file() else ""
    lines += [f"  fix {m.group(1)}: {m.group(2).strip()[:400]}" for m in re.finditer(r"(?m)^\s*(\d+)\.\s[^\n]*?->\s*([^\n]+)", text)]
    lines += [f"  keep: {m.group(1).strip()[:400]}" for m in re.finditer(r"(?mi)^\s*keep:\s*([^\n]+)", text)][:1]
    lines.append("  Then render, run the checks, and give the new render to a fresh art-director.")
    return "\n".join(lines)


def cmd_grade(a):
    piece = load_piece(a.slug)
    stage = a.stage
    rub = load("rubrics")["stages"][stage]
    st = piece["stages"][stage]
    if st.get("status") == "skipped":
        sys.exit(f"stage '{stage}' is not part of the {piece.get('scope')} path. To see what to do, run:\n  {me('next', a.slug)}")
    ind = needs_critic(piece, stage)
    try:
        scores = {k.strip(): float(v) for k, v in (p.split("=") for p in a.scores.split(",") if p.strip())}
    except ValueError:
        sys.exit("scores must look like: novelty=8,truth=9")
    names = [c["id"] for c in rub["criteria"]]
    missing = [n for n in names if n not in scores]
    if missing:
        sys.exit(f"missing scores for: {', '.join(missing)}")
    if any(not 1 <= s <= 10 for s in scores.values()):
        sys.exit("scores run from 1 to 10")
    if ind and a.by != "critic":
        sys.exit(f"stage '{stage}' must be graded by an independent critic (--by critic): the author does not mark their own work here")
    if a.notes and not pathlib.Path(a.notes).is_file():
        sys.exit(f"--notes {a.notes}: no such file. Write one line per criterion, \"criterion: reason\" (the template is at the end of the worksheet).")
    notes = pathlib.Path(a.notes).read_text(encoding="utf-8") if a.notes else ""
    weak = [n for n in names if not re.search(rf"^\s*-?\s*{re.escape(n)}\s*[:=].{{25,}}", notes, flags=re.M | re.I)]
    if weak:
        sys.exit(f"every score needs a 'because' line in the notes (criterion: evidence, 25+ characters). Missing or thin: {', '.join(weak)}\n{grade_block(piece, stage)}")
    vague = re.findall(r"\b(pop|clean|modern|sleek|feels off|nice|good job|great|amazing|elevate)\b", notes, flags=re.I)
    if len(vague) >= 3:
        sys.exit(f"the notes lean on vague words ({', '.join(sorted(set(v.lower() for v in vague)))}); name the mechanism instead (size, contrast, spacing, order, a quoted line)")
    ev = check_evidence(a.evidence, "the critic's verdict file for this stage", pathlib.Path(a.notes), ids=names, best=stage == "angles", slug=a.slug) if ind or a.evidence else None
    ev = ev or {}
    theirs = ev.get("scores", {})   # what the critic's file says about each criterion; the author may not grade it upward
    off = [f"{k}: the file says {theirs[k]:g}, --scores says {scores[k]:g}" for k in theirs if abs(theirs[k] - scores[k]) > 0.05]
    if off:
        sys.exit("--scores must be the critic's own numbers, and they differ from the --evidence file (" + "; ".join(off) + "). Type what the file says, or have the critic grade again.")
    wsum = sum(c["weight"] for c in rub["criteria"])
    total = sum(scores[c["id"]] * c["weight"] for c in rub["criteria"]) / wsum
    capped = []
    for cap in rub.get("caps", []):
        if check_cap(cap["if"], scores, a.swap) and total > cap["max_total"]:
            total = cap["max_total"]
            capped.append(cap["if"])
    total = math.floor(total * 10) / 10
    said, whole = ev.get("total"), len(theirs) == len(names)   # whole: the file scores every criterion, so its own total is only a note
    if said is not None and not whole and abs(said - total) > 0.1:
        sys.exit(f"--scores give a total of {total:g}, but the --evidence file states a total of {said:g}: type the critic's numbers, or have the critic grade again.")
    bad = ev.get("verdict") in ("FAIL", "REVISE")
    if bad and total >= rub["threshold"] and not whole:
        sys.exit(f"the --evidence verdict is {ev['verdict']}, yet --scores reach {total:g} and the file gives no scores of its own to hold them to: the numbers must be the critic's. Nothing is recorded.")
    passed = total >= rub["threshold"] and not bad
    if passed and stage == "visual":
        ev["render"] = check_render(piece, a.folder)
        piece.setdefault("visual_html", ev["render"]["html"])   # a piece built without scaffold now names its page too
    kept = keep_attempt(piece, a.folder, st.get("attempts", 0) + 1, a.evidence) if stage == "visual" else None
    st.setdefault("grades", []).append({"at": dt.datetime.now().isoformat(timespec="seconds"), "by": a.by, "scores": scores,
                                        "total": total, "capped": capped, "passed": passed, "notes": notes[:4000], **({"evidence": ev} if ev else {}),
                                        **({"attempt": str(kept)} if kept else {})})
    st["attempts"] = st.get("attempts", 0) + 1
    if passed:
        st["status"] = "passed"
    elif st["attempts"] >= rub["max_attempts"]:
        st["status"] = "escalated"
    else:
        st["status"] = "recreate" if rub["on_fail"] == "recreate" else "revise"
    save_piece(piece)
    why = ("capped by " + "; ".join(capped) if capped else "") + (", " if capped and bad else "") + ("the critic's verdict is " + str(ev["verdict"]) if bad else "")
    print(f"{stage}: {total} (threshold {rub['threshold']}{', ' + why if why else ''}) -> {st['status'].upper()}")
    if said is not None and whole and abs(said - total) > 0.1:
        print(f"  note: the critic's own total is {said:g}; the rubric's weights give {total:g}, and that is the grade")
    if not passed:
        low = sorted(scores.items(), key=lambda kv: kv[1])[:2]
        print("  lowest: " + ", ".join(f"{k} {v:g}" for k, v in low))
    return 0 if passed else 1


# ---------- navigation ----------

def current(piece):
    for s in STAGES:
        if piece["stages"][s].get("status") not in DONE:
            return s
    return None


def cmd_next(a):
    piece = load_piece(a.slug)
    s = current(piece)
    if not s:
        if piece.get("scope") == "design":
            print("Design stages passed. Build and render the piece. Deliver only after the host approves it:\n  " + me("deliver", piece["slug"]))
            pc = palette_missing(piece)
            if pc:
                print("Colour first, in the folder where the page will live (it writes palette.css, which scaffold links):\n  " + pc)
            print("Start the page:\n  " + me("scaffold", piece["slug"]))
            return 0
        if piece.get("scope") == "quick":
            print(f"Quick stages passed (atoms, angles, genome, visual). Deliver:\n  {me('deliver', piece['slug'])}")
            return 0
        print(f"every stage passed. Deliver:\n  {me('deliver', piece['slug'])}")
        return 0
    st = piece["stages"][s]
    status = st.get("status", "pending")
    best = max((g["total"] for g in st.get("grades", [])), default=None)
    if status == "escalated":
        kept = next((g["attempt"] for g in sorted(st.get("grades", []), key=lambda g: -g["total"]) if g.get("attempt")), None)
        print(f"{s}: ESCALATE. {st['attempts']} attempts, best {best}{f' (kept in {pp(kept)})' if kept else ''}. Show the person the best attempt and the critics' lowest criteria; ask whether to change the topic, the material or the bar. Do not lower the bar yourself.")
        return 1
    if status == "recreate":
        print(f"{s}: RECREATE (attempt {st['attempts'] + 1}). Deal again; the new deal excludes everything already tried:")
        print(f"  {me('deal', piece['slug'], s)}" if s in {"lenses", "angles", "genome"} else f"  rebuild the {s} from scratch with the critique's three worst problems")
        return 0
    if status == "revise" and s == "visual" and st.get("grades"):
        print(revise_from_best(piece, st))
        return 0
    if status == "revise":
        print(f"{s}: REVISE (attempt {st['attempts'] + 1}). Fix the three lowest criteria only (constructive critique in references/critique.md), keep what scored highest, then grade again.")
        return 0
    if piece.get("scope") == "design" and s in {"atoms", "lenses", "angles"}:
        print(f"{s}: design scope. Adopt the host's approved angle:\n  " + me("adopt", piece["slug"], '--angle "<one line>"', "--operator <id>", "--evidence <host-grading-record.md>"))
        return 0
    if s in {"lenses", "angles", "genome"} and not st.get("deals"):
        print(f"{s}: deal it:\n  {me('deal', piece['slug'], s)}")
        return 0
    if s == "genome" and not piece.get("angle"):
        print("angles passed: record the winner first:\n  " + me("choose", piece["slug"], "angle", "<n>", '--text "<its one line>"'))
        return 0
    ws = pp(PIECES / piece["slug"] / f"{STAGES.index(s) + 1:02d}-{s}.md")
    pc = palette_missing(piece) if s == "visual" else None   # scaffold links palette.css only when it exists, so the colour comes first
    page = pathlib.Path(piece["visual_html"]) if piece.get("visual_html") else None   # once scaffold wrote the page, a second scaffold refuses: point at the page instead
    grade_it = "Then grade it (the notes template is at the end of the worksheet):"
    if s != "visual":
        print(f"{s}: fill {ws}. {grade_it}")
    else:   # every command on a line of its own, so a whole-line copy runs as printed in PowerShell and in Git Bash
        work = (f"render it, write the post text that goes with it (post.md: every claim on the page is in it), and give the renders and the post text "
                f"to the art-director agent. Then fill {ws}. {grade_it}")
        lead = "visual: "
        if pc:
            print("visual: colour first, in the folder where the page will live (it writes palette.css, which scaffold links):")
            print("  " + pc)
            lead = "Then "
        if page and page.is_file():
            print(f"{lead}build the page scaffold wrote ({pp(page)}), {work}")
        else:
            print(f"{lead}start the page:")
            print("  " + me("scaffold", piece["slug"]))
            print(f"Build it, {work}")
    print("  " + grade_cmd(piece, s))
    return 0


def cmd_new(a):
    if piece_path(a.slug).exists():
        sys.exit(f"piece '{a.slug}' exists")
    if a.brand and not pathlib.Path(a.brand).is_file():
        sys.exit(f"--brand {a.brand}: no such file. Give the brand's tokens.css (colour custom properties), as palette.py --brand takes it.")
    piece = {"slug": a.slug, "topic": a.topic, "topic_key": sorted(topic_key(a.topic)), "medium": a.medium, "scope": a.scope,
             "created": dt.datetime.now().isoformat(timespec="seconds"), "stages": {s: {"status": "pending"} for s in STAGES},
             **({"brand": str(pathlib.Path(a.brand).resolve())} if a.brand else {})}
    if a.scope == "design":
        for s in HOST_STAGES:
            piece["stages"][s]["status"] = "host"
        save_piece(piece)
        print(f"piece {a.slug}: {a.medium}, design scope (the host system writes, critiques and approves; the composer deals the design and remembers it).")
        print("  next:")
        print("    " + me("adopt", a.slug, '--angle "<the approved angle in one line>"', "--operator <closest id in data/operators.json>", "--evidence <the host grading record, a file>"))
        return 0
    if a.scope == "quick":
        for s in QUICK_SKIP:
            piece["stages"][s]["status"] = "skipped"
    save_piece(piece)
    ws_atoms(piece)
    for s in ("visual",) if a.scope == "quick" else ("sections", "copy", "visual", "final"):
        ws_generic(piece, s)
    prior = same_topic_runs(piece, history())
    print(f"piece {a.slug}: {a.medium}{', quick scope: atoms, angles, genome and visual; only the visual needs a critic' if a.scope == 'quick' else ''}. Worksheets in {pp(PIECES / a.slug)}.")
    if prior:
        print(f"  this topic was made {len(prior)} time(s) before: those operators, lenses, formats and directions are excluded from every deal.")
    print(f"  next: fill {pp(PIECES / a.slug / '01-atoms.md')}, then grade it (the notes template is at the end of the worksheet):")
    print("    " + grade_cmd(piece, "atoms"))
    print("  Lost? Run:")   # the label and the command on lines of their own, so a whole-line copy runs as printed
    print("    " + me("next", a.slug))
    return 0


def cmd_deal(a):
    piece = load_piece(a.slug)
    s = a.stage
    idx = STAGES.index(s)
    if piece["stages"][s].get("status") == "skipped":
        sys.exit(f"stage '{s}' is not part of the {piece.get('scope')} path. To see what to do, run:\n  {me('next', a.slug)}")
    if any(piece["stages"][p].get("status") not in DONE for p in STAGES[:idx]):
        sys.exit(f"earlier stages must pass first: {', '.join(p for p in STAGES[:idx] if piece['stages'][p].get('status') not in DONE)}")
    if s == "genome" and not piece.get("angle"):
        sys.exit("choose the winning angle first:\n  " + me("choose", a.slug, "angle", "<n>", '--text "<its one line>"'))
    if a.any_type and s != "genome":
        sys.exit("--any-type is for the genome: it lets the deal use type from taste-skill's library, whose families need get_font.py")
    if a.pin and s != "genome":
        sys.exit("--pin is for the genome: it fixes axes of the dealt design (for example register=warmth) and the rest is dealt around them")
    if a.pin:   # kept with the piece, so a re-deal keeps the pin; a pin on the same axis replaces the earlier one
        piece["pins"] = {**piece.get("pins", {}), **parse_pins(a.pin, piece["medium"])}
    f = deal_genome(piece, a.seed, a.any_type) if s == "genome" else {"lenses": deal_lenses, "angles": deal_angles}[s](piece, a.seed)
    if piece["stages"][s].get("status") in {"recreate", "pending"}:
        piece["stages"][s]["status"] = "dealt"
    save_piece(piece)
    print(f"{s} dealt -> {pp(f)}")
    print(f.read_text(encoding="utf-8"))
    return 0


def cmd_choose(a):
    piece = load_piece(a.slug)
    deal = piece["stages"]["angles"].get("deals", [[]])[-1]
    n = int(a.n)
    if not 1 <= n <= len(deal):
        sys.exit(f"angle number must be 1 to {len(deal)}")
    lenses = piece["stages"]["lenses"].get("deals", [[]])[-1]
    piece["angle"] = {"n": n, "operator": deal[n - 1], "lens": lenses[(n - 1) % len(lenses)] if lenses else "", "one_line": a.text or ""}
    save_piece(piece)
    print(f"angle {n}: operator {deal[n - 1]}, lens {piece['angle']['lens'] or '(none)'}. Next:")
    cmd_next(a)   # the real next step: deal the genome once the angles stage passed; after a RECREATE or REVISE grade, what that grade asks
    return 0


def parse_pins(text, medium):
    """--pin axis=value,...: axes of the genome decided before the deal (a host's direction rotation, a register to exercise). Each value must be one of its axis's options for the medium."""
    pins, axes = {}, genome_axes(medium)
    for part in filter(None, (x.strip() for x in (text or "").split(","))):
        ax, _, v = part.partition("=")
        if ax not in axes or v not in axes[ax]:
            sys.exit(f"--pin {part}: the axis must be one of {', '.join(axes)} and the value one of its options for {medium} (data/)")
        pins[ax] = v
    return pins


def cmd_adopt(a):
    """Design scope: take an angle that another graded system (for example a content engine's angle gate) has already passed."""
    piece = load_piece(a.slug)
    if piece.get("scope") != "design":
        sys.exit("adopt is only for pieces made with --scope design; a full piece earns its angle through the angles stage")
    ev = check_evidence(a.evidence, "the host's grading record for this angle", angle=a.angle)
    ops = {o["id"] for o in load("operators")}
    if a.operator not in ops:
        sys.exit(f"--operator must be the closest play operator in data/operators.json, one of: {', '.join(sorted(ops))}")
    pins = parse_pins(a.pin, piece["medium"])
    hist = history()
    top = max((jaccard(trigrams(a.angle), trigrams(h.get("angle", ""))) for h in hist if h.get("angle")), default=0.0)
    if top >= 0.25:
        sys.exit(f"this angle overlaps a remembered one by {top:.2f} (0.25 or more): recreate it in the host system first")
    for s in ("atoms", "lenses", "angles"):
        piece["stages"][s].update(status="passed", adopted=ev["path"])
    piece["stages"]["angles"]["deals"] = [[a.operator]]
    piece["angle"] = {"n": 0, "operator": a.operator, "lens": "", "one_line": a.angle, "evidence": ev["path"], "evidence_sha256": ev["sha256"]}
    piece["pins"] = pins
    save_piece(piece)
    print(f"adopted (overlap with memory {top:.2f}). Next:\n  {me('deal', a.slug, 'genome')}")
    return 0


def cmd_similar(a):
    hist = history()
    me = trigrams(a.text)
    rows = sorted(((jaccard(me, trigrams(h.get("angle", ""))), h.get("slug"), h.get("angle", "")) for h in hist if h.get("angle")), reverse=True)[:3]
    top = rows[0][0] if rows else 0.0
    verdict = "too close: recreate" if top >= 0.25 else "close: sharpen the difference" if top >= 0.12 else "new"
    print(f"novelty: max overlap {top:.2f} with memory ({len(hist)} pieces) -> {verdict}")
    for j, s, t in rows:
        print(f"  {j:.2f} {s}: {t[:90]}")
    return 1 if top >= 0.25 else 0


def cmd_status(a):
    piece = load_piece(a.slug)
    print(f"{piece['slug']} ({piece['medium']}): {piece['topic']}")
    for s in STAGES:
        st = piece["stages"][s]
        g = st.get("grades", [])
        print(f"  {s:9} {st.get('status', 'pending'):10} attempts {st.get('attempts', 0)}  last {g[-1]['total'] if g else '-'}")
    if piece.get("genome"):
        print("  genome: " + ", ".join(f"{k}={v}" for k, v in piece["genome"].items() if k != "layout_rhythm"))
    return 0


def remember_cover(piece):
    """Add the delivered cover (page-01.png, or poster.png for a film) to the layout memory, so layout_memory.py check has covers to compare with."""
    folder = pathlib.Path(piece["visual_html"]).parent if piece.get("visual_html") else None
    cover = next((c for c in ((folder / "poster.png") if piece["medium"] == "video" else None, folder / "page-01.png" if folder else None) if c and c.is_file()), None)
    if not cover:
        print(f"no cover to remember: there is no page-01.png next to the page. Once it is rendered, run:\n  {PY} {tool('layout_memory.py')} add <cover> --name {piece['slug']}")
        return
    r = subprocess.run([sys.executable, str(SCRIPTS / "layout_memory.py"), "add", str(cover), "--name", piece["slug"], "--memory", str(HOME / "covers")], capture_output=True, text=True)
    print(f"cover {r.stdout.strip() or 'not remembered'}" if r.returncode == 0 else f"cover not remembered ({(r.stderr.strip().splitlines() or ['layout_memory.py failed'])[-1]}). Run:\n  {PY} {tool('layout_memory.py')} add {q(cover)} --name {piece['slug']}")


def cmd_deliver(a):
    piece = load_piece(a.slug)
    if current(piece):
        sys.exit(f"not every stage has passed (now at: {current(piece)}); nothing is written to memory")
    HOME.mkdir(parents=True, exist_ok=True)
    angle = piece.get("angle", {})
    evidence = {s: piece["stages"][s]["grades"][-1]["evidence"] for s in STAGES if piece["stages"][s].get("grades") and piece["stages"][s]["grades"][-1].get("evidence")}
    if angle.get("evidence"):   # an angle adopted in design scope: the host's grading record
        evidence["angles"] = {"path": angle["evidence"], "sha256": angle.get("evidence_sha256", "")}
    entry = {"date": dt.date.today().isoformat(), "slug": piece["slug"], "topic": piece["topic"], "topic_key": piece["topic_key"],
             "medium": piece["medium"], "scope": piece.get("scope", "full"), "genome": piece.get("genome", {}), "angle": angle.get("one_line", ""),
             "operators": piece["stages"]["angles"].get("deals", [[]])[-1], "lenses": piece["stages"]["lenses"].get("deals", [[]])[-1],
             "scores": {s: piece["stages"][s]["grades"][-1]["total"] for s in STAGES if piece["stages"][s].get("grades")}, "evidence": evidence}
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"delivered {piece['slug']}: remembered in {pp(HISTORY)}. Future deals now avoid it.")
    remember_cover(piece)
    print(f"Also remember the look, with Python Playwright:\n  {PY} {q(SKILL / 'vendor' / 'huashu-design' / 'scripts' / 'design_lint.py')} ledger add <file.html> --project {piece['slug']}")
    return 0


# ---------- scaffold ----------

# every relative link in a specimen: href, src, poster, url(...) and @import "..."
LINK = re.compile(r"""(?:\b(?:href|src|poster)\s*=\s*["']|url\(\s*["']?|@import\s+["'])(?P<u>(?![a-zA-Z][a-zA-Z0-9+.\-]*:|[/#\s])[^"')\s>]+)""")
SECTION = re.compile(r"""<section\b[^>]*\bclass="[^"]*\bpage\b[^"]*"[^>]*>.*?</section>""", re.S)
PG = re.compile(r"\s*pg-\d+")
GROUND = {"dark": ("night", "cream"), "paper": ("paper", "ink"), "field": ("house", "cream")}
MINIMAL = """<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="../tokens.css">
<!-- Minimal page for the direction "@DIR@" (@WHY@): the @GROUND@ ground. Colour comes from the palette.css roles (--ground, --text, --text-2, --accent) when it is linked, else from tokens.css. Type comes from --disp, --body and --mono. -->
<style>
.mn { background: var(--ground, var(--@BG@)); color: var(--text, var(--@FG@)); padding: 90px 80px; }
.mn h1 { font: 650 110px/0.98 var(--disp); letter-spacing: -0.03em; max-width: 920px; }
.mn .bar { width: 160px; height: 10px; margin-top: 44px; background: var(--accent, var(--teal-lit)); }
.mn p { margin-top: 28px; font: 450 40px/1.3 var(--body); }
.mn .claim { position: absolute; left: 80px; right: 80px; top: 620px; margin-top: 0; }
.mn .fine { position: absolute; left: 80px; right: 80px; bottom: 54px; margin: 0; font-size: 24px; color: var(--text-2, var(--@FG@)); }
.mn.wide { padding: 110px 120px; }
.mn.wide h1 { font-size: 124px; max-width: 1400px; }
.mn.wide .claim { left: 120px; right: 120px; top: 560px; max-width: 1100px; }
.mn.wide .fine { left: 120px; right: 120px; bottom: 60px; }
</style>
<section class="page mn@WIDE@">
  <h1 data-role="hook">Replace this with the hook.</h1>
  <div class="bar"></div>
  <p class="claim">Replace this with the claim and its proof.</p>
  <p class="fine" data-role="fine">Replace this with the source.</p>
</section>
"""
# The composition start (image and carousel pages of a direction with a specimen). It is not the specimen: the specimen's frame and sample words
# stay out of the page, because the art-director judges distinct against that specimen. It gives the grid, the dealt type and the palette roles,
# and sets each page up for its dealt layout word (data/structures.json "layouts"); the builder draws the object in the direction's grammar.
START = """<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="../tokens.css">
<!-- Composition start for the direction "@DIR@" on the @GROUND@ ground. Not the specimen: the grid, the dealt type and the palette.css roles, each page set up for its dealt layout word.
     Read the specimen for the grammar's rules (@SPEC@); do not repeat its frame (@FRAME@) or its stock parts unchanged (04-genome.md lists them): draw the device as your object. Word budget: @BUDGET@ words a page, the hook @HOOK@ or fewer (references/copy.md). -->
<style>
/* the grid (references/composition.md): one left margin at 80 px, 88 px at the top, 104 px at the foot, gaps on an 8 px scale */
.st { display: grid; gap: 40px; padding: 88px 80px 104px; background: var(--ground, var(--@BG@)); color: var(--text, var(--@FG@)); }
.st > * { margin: 0; min-width: 0; }
.st > :is(h1, h2) { grid-area: hook; font: 650 calc(var(--hook, 100px) * var(--hook-scale, 1))/0.98 var(--disp); letter-spacing: -0.03em; text-wrap: balance; }
.st > .num { grid-area: number; align-self: end; font: 700 400px/0.8 var(--disp); letter-spacing: -0.05em; }
.st > .object { grid-area: object; border: 3px dashed var(--text-2, var(--@FG@)); padding: 32px; font: 500 40px/1.3 var(--body); color: var(--text-2, var(--@FG@)); }
.st > .proof { grid-area: proof; font: 450 40px/1.3 var(--body); text-wrap: pretty; }
.st > .fine { grid-area: fine; align-self: end; max-width: 760px; font: 500 36px/1.3 var(--body); }
.st > .logo { right: 80px; bottom: 48px; }
/* one arrangement per layout word; change the sizes to fit the material, keep the arrangement */
.st.stack { grid-template-rows: auto 1fr auto auto; grid-template-areas: "hook" "object" "proof" "fine"; }
.st.split { --hook: 84px; grid-template-columns: 7fr 5fr; grid-template-rows: auto auto 1fr; grid-template-areas: "hook object" "proof object" "fine object"; }
.st.bleed { grid-template-rows: 1fr auto auto auto; grid-template-areas: "." "hook" "proof" "fine"; }
.st.bleed > .object { grid-area: auto; position: absolute; left: 300px; top: -80px; width: 880px; height: 800px; display: flex; align-items: flex-end; }
.st.grid { --hook: 88px; grid-template-columns: repeat(4, 1fr); grid-template-rows: repeat(3, 1fr) auto auto auto; grid-template-areas: ". object object object" ". object object object" ". object object object" "hook hook hook ." "proof proof proof ." "fine fine fine fine"; }
.st.table { grid-template-rows: 1fr auto auto auto; grid-template-areas: "object" "hook" "proof" "fine"; }
.st.table > h1, .st.table > h2 { border-top: 8px double var(--text, var(--@FG@)); padding-top: 24px; }
.st.map { --hook: 88px; grid-template-columns: 1fr 1fr; grid-template-rows: auto auto 1fr auto; grid-template-areas: ". hook" ". proof" ". ." "fine fine"; }
.st.map > .object { grid-area: auto; position: absolute; inset: 56px 40px 200px; display: flex; align-items: flex-end; }
.st.diagram { --hook: 84px; grid-template-rows: 1fr auto auto auto; grid-template-areas: "object" "hook" "proof" "fine"; }
.st.quote { --hook: 120px; grid-template-rows: 1fr auto auto auto; grid-template-areas: "hook" "object" "proof" "fine"; }
.st.quote > h1, .st.quote > h2 { align-self: end; }
.st.number { --hook: 72px; grid-template-columns: 7fr 5fr; grid-template-rows: 1fr auto auto; grid-template-areas: "number number" "hook proof" "fine fine"; }
.st.artefact { --hook: 84px; grid-template-rows: 1fr auto auto auto; grid-template-areas: "." "hook" "proof" "fine"; }
.st.artefact > .object { grid-area: auto; position: absolute; left: 80px; top: 88px; width: 1060px; height: 700px; }
.st.sequence { --hook: 84px; grid-template-columns: 5fr 7fr; grid-template-rows: 1fr auto auto; grid-template-areas: "object object" "proof hook" "fine fine"; }
.st.field { --hook: 120px; grid-template-rows: 1fr auto auto auto; grid-template-areas: "." "hook" "proof" "fine"; }
</style>
@PAGES@
"""


HOOK_SAMPLE = "Your&nbsp;hook, in&nbsp;eight words or&nbsp;fewer."   # small words tied to the next, in chunks narrow enough for the narrowest hook column


def start_pages(direction, rhythm, jobs):
    """The <section> of each page of the composition start: the layout word as its class and the parts that layout places.
    The number layout leads with a number (data-role number) instead of an object; the field layout has no object.
    A later page's heading is two chunks no wider than the sample hook's, and its job goes in the proof line: a job word at display size ("consequence") overran the map layout's half-width hook column."""
    out = []
    for i, word in enumerate(rhythm, 1):
        job = jobs[i - 1] if i <= len(jobs) else "extra"
        head = (f'  <h1 data-role="hook">{HOOK_SAMPLE}</h1>' if i == 1 else
                f'  <h2>Page&nbsp;{i}: its&nbsp;hook.</h2>')
        parts = ['  <p class="num" data-role="number">N</p>'] if word == "number" else []
        parts.append(head)
        if word not in ("number", "field"):
            allow = ' data-allow="bleed"' if word in ("bleed", "artefact") else ""
            parts.append(f'  <div class="object" data-role="object"{allow}>The object, drawn in the {direction} grammar.</div>')
        proof = "One line of proof." if i == 1 else f"{job[:1].upper()}{job[1:]}: one line of proof."
        parts += [f'  <p class="proof">{proof}</p>', '  <p class="fine" data-role="fine">The source.</p>']
        if i == 1:
            parts.append('  <img class="logo" data-role="logo" src="data:," alt=""><!-- logo slot: scaffold points it at the brand file\'s --logo, or removes it -->')
        out.append(f'<section class="page st {word} pg-{i}">\n  <!-- page {i}: {job}; layout "{word}": {load("structures").get("layouts", {}).get(word, "")} -->\n' + "\n".join(parts) + "\n</section>")
    return "\n".join(out)


def absolute_links(html, base):
    """Rewrite every relative link in html to a file:/// URL, resolved against base. Returns the html and the links that point nowhere."""
    missing = []

    def fix(m):
        path, tail = re.match(r"([^?#]*)(.*)", m.group("u"), re.S).groups()
        target = (base / urllib.parse.unquote(path)).resolve()
        if not target.exists():
            missing.append(m.group("u"))
            return m.group(0)
        return m.group(0)[:m.start("u") - m.start()] + target.as_uri() + tail
    return LINK.sub(fix, html), missing


TOKENS_LINK = re.compile(r"<link\b[^>]*\btokens\.css[^>]*>")
LOGO_TAG = re.compile(r"""[ \t]*<img\b[^>]*\bdata-role\s*=\s*["']logo["'][^>]*>[ \t]*\n?""")


def brand_css(brand):
    """The brand file's text without its comments, so a commented-out line (as in assets/brands/TEMPLATE.css) declares nothing."""
    return re.sub(r"/\*.*?\*/", "", brand.read_text(encoding="utf-8", errors="replace"), flags=re.S) if brand and brand.is_file() else ""


def brand_sets(brand, names):
    """The custom properties among `names` that the brand file declares (names without the leading --)."""
    css = brand_css(brand)
    return [n for n in names if re.search(r"(?<![\w-])--" + n + r"\s*:", css)]


def brand_logo(brand, dark=False):
    """(uri, declared) of the logo a brand file declares with `--logo: url(...)`; on a dark ground or a colour field `--logo-on-dark` comes first. A relative path is read against the brand file; uri is None when nothing is declared or the file is not there."""
    text = brand_css(brand)
    for name in (("--logo-on-dark",) if dark else ()) + ("--logo",):
        m = re.search(name + r"""\s*:\s*url\(\s*["']?([^"')]+?)["']?\s*\)""", text)
        if m:
            u = m.group(1).strip()
            if re.match(r"(?:https?|file|data):", u, re.I):
                return u, True
            p = pathlib.Path(urllib.parse.unquote(u))
            p = (p if p.is_absolute() else brand.parent / p).resolve()
            return (p.as_uri() if p.is_file() else None), True
    return None, False


def fit_logo(html, brand, dark=False):
    """The specimens carry an empty logo slot. Fill it from the brand file (--logo, or --logo-on-dark when the ground is dark or a colour field): point the img at it. Otherwise remove it.
    Returns the html and the line to print, or None when the page has no logo."""
    if not LOGO_TAG.search(html):
        return html, None
    uri, declared = brand_logo(brand, dark)
    if uri:
        point = lambda m: re.sub(r'\balt\s*=\s*"[^"]*"', 'alt="logo"', re.sub(r'\bsrc\s*=\s*"[^"]*"', lambda _: f'src="{uri}"', m.group(0)))
        return LOGO_TAG.sub(point, html), f"logo: the brand file's --logo ({uri})"
    why = ("the brand file's --logo points at a file that is not there" if declared else "the brand file declares no --logo") if brand else "no --brand file, so no logo"
    return LOGO_TAG.sub("", html), f'logo removed: {why}; add your own with data-role="logo"'


def palette_roles(direction, pal):
    """The <style> that makes a specimen follow palette.css: its token names (--night, --cream, --house ...) are set to the palette roles (data/directions.json "roles"),
    and "rules" restyles what the specimen draws in a fixed colour (an SVG stroke, a ground). The roles live on .pg-N, so the block sits on .page, where --ground and the rest exist."""
    d = next((d for d in load("directions") if d["id"] == direction), {})
    if not (pal and d.get("roles")):
        return None
    tokens = "; ".join(f"--{k}: {v}" for k, v in d["roles"].items())
    return "<style>/* the direction's colour tokens follow the palette.css roles (data/directions.json) */\n.page { " + tokens + "; }\n" + "\n".join(d.get("rules", [])) + "\n</style>"


def palette_missing(piece):
    """The palette.py line when no palette.css is where scaffold looks for it (next to the scaffolded page, else the current folder); else None."""
    here = [pathlib.Path(piece["visual_html"]).parent] if piece.get("visual_html") else []
    return None if any((c / "palette.css").is_file() for c in (*here, pathlib.Path.cwd())) or not piece.get("genome") else palette_cmd(piece["genome"], piece.get("brand"))


def cmd_scaffold(a):
    """Start the page: the dealt direction's specimen (or a minimal page on tokens.css), links made absolute, pages and size from the genome."""
    piece = load_piece(a.slug)
    g = piece.get("genome")
    if not g:
        sys.exit(f"no genome yet: deal it first:\n  {me('deal', a.slug, 'genome')}")
    out = pathlib.Path(a.out).resolve()
    if out.exists() and not a.force:
        sys.exit(f"{pp(out)} exists and scaffold would overwrite your page: pick another file with --out, or start again with --force")
    med, direction = piece["medium"], g["direction"]
    pages = 1 if med == "video" else len(g["layout_rhythm"])   # a motion page is one section that moves
    w, h = SIZES.get(med, (1080, 1350))
    wide = (w, h) != (1080, 1350)
    bg, fg = GROUND.get(g["ground"], GROUND["paper"])   # the ground's colours on tokens.css, the fallback when palette.css is not linked
    spec = specimen(direction, med)   # a slide (1920x1080) never starts from a 1080x1350 specimen, or the audit fails with text over text
    composed = bool(spec) and med in COMPOSED
    jobs = next((f["sections"] for f in load("formats") if f["id"] == g["format"]), [])
    d = next((x for x in load("directions") if x["id"] == direction), {})
    if composed:   # not the specimen's page: the art-director judges distinct against it, so its frame and sample words stay out
        html = (START.replace("@DIR@", direction).replace("@GROUND@", g["ground"]).replace("@BG@", bg).replace("@FG@", fg).replace("@SPEC@", pp(spec))
                .replace("@FRAME@", d.get("frame", "")).replace("@BUDGET@", str(WORD_BUDGET)).replace("@HOOK@", str(HOOK_WORDS))
                .replace("@PAGES@", start_pages(direction, g["layout_rhythm"][:pages], jobs)))
    elif spec:
        html = spec.read_text(encoding="utf-8")
    else:
        why = "a slide is 1920x1080 and the specimens are not; assets/directions/slide-16x9.html is a 16:9 layout to borrow" if med == "slide" else "it has no specimen yet"
        html = MINIMAL.replace("@DIR@", direction).replace("@WHY@", why).replace("@GROUND@", g["ground"]).replace("@BG@", bg).replace("@FG@", fg).replace("@WIDE@", " wide" if wide else "")
    html, missing = absolute_links(html, SPECS)
    brand = pathlib.Path(piece["brand"]) if piece.get("brand") else None
    if brand and brand.is_file():   # the person's colours load right after tokens.css, so the page's tokens read them
        html = TOKENS_LINK.sub(lambda m: m.group(0) + f'<link rel="stylesheet" href="{brand.as_uri()}">', html, count=1)
    html, logo = fit_logo(html, brand, g["ground"] in ("dark", "field"))
    secs = list(SECTION.finditer(html))
    if not secs:
        sys.exit(f"{pp(spec) if spec else 'the minimal page'} has no <section class=\"page\">: nothing to build on")
    keep = secs[:pages]
    classes = PG.sub("", re.search(r'class="([^"]*)"', keep[0].group(0)).group(1))
    tint = f"var(--{fg})" if spec else f"var(--text, var(--{fg}))"   # a placeholder page must be readable on its ground (index-card sets a background and no colour)
    cover = [re.sub(r'(<section\b[^>]*\bclass=")([^"]*)"', lambda m, i=i: f'{m.group(1)}{PG.sub("", m.group(2))} pg-{i}"', m_.group(0), count=1) for i, m_ in enumerate(keep, 1)]
    more = [f'<section class="{classes} pg-{i}">\n  <!-- page {i}: {jobs[i - 1] if i <= len(jobs) else "extra"}; layout {g["layout_rhythm"][i - 1]} -->\n'
            f'  <p class="fine" data-role="fine" style="color: {tint}">Page {i}: {jobs[i - 1] if i <= len(jobs) else "extra"}. Layout: {g["layout_rhythm"][i - 1]}. Replace with the real page.</p>\n</section>'
            for i in range(len(keep) + 1, pages + 1)]
    lead = [f"<!-- atelier scaffold for {a.slug}: direction {direction}, format {g['format']}, {pages} page(s). Layout rhythm: {' > '.join(g['layout_rhythm'])}. Field page: {g.get('field_page', 'none')}. Replace the sample content. -->"]
    if wide:
        lead.append(f"<style>@page {{ size: {w}px {h}px; margin: 0; }} section.page {{ width: {w}px; height: {h}px; }}</style>")
    pal = next((c for c in (out.parent / "palette.css", pathlib.Path.cwd() / "palette.css") if c.is_file()), None)
    roles = palette_roles(direction, pal) if spec else None
    if pal:
        lead.append(f'<link rel="stylesheet" href="{pal.resolve().as_uri()}">')
    if roles:
        lead.append(roles)
    disp, text, mono, local = type_families(g["type"])
    library = FONTS / "library" / "library.css"
    keeps = bool(next((d for d in load("directions") if d["id"] == direction), {}).get("keeps_house_type"))
    kept = brand_sets(brand, ("disp", "body", "mono"))   # faces the brand file declares itself: the dealt pairing does not replace them
    fams = {"disp": f"\"{disp}\", system-ui, sans-serif", "body": f"\"{text}\", system-ui, sans-serif", "mono": f"\"{mono}\", ui-monospace, monospace"}
    fams = {k: v for k, v in fams.items() if k not in kept}
    if local and not keeps and fams and library.is_file():   # the dealt pairing's families, loaded from the skill's own font library
        # a wide display face sets the start's hook smaller (data/type_pairings.json "hook_scale"), so the sample hook fits the narrowest hook column
        scale = next((x.get("hook_scale") for x in load("type_pairings") if x["id"] == g["type"]), None) if "disp" in fams else None
        lead += [f'<link rel="stylesheet" href="{library.as_uri()}">', "<style>:root { " + "; ".join(f"--{k}: {v}" for k, v in fams.items())
                 + (f"; --hook-scale: {scale}" if scale else "") + "; }</style>"]
    html = html[:secs[0].start()] + "\n".join(lead + cover + more) + html[secs[-1].end():]
    hook = "found"
    if not re.search(r"""data-role\s*=\s*["']hook["']""", html):
        html, n = re.subn(r"<(h[1-3])\b(?![^>]*data-role)", r'<\1 data-role="hook"', html, count=1)
        hook = "added to the first heading" if n else "NOT FOUND: add data-role=\"hook\" to the hook element"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    piece["visual_html"] = str(out)   # grade visual looks for the render next to this page
    save_piece(piece)
    print(f"scaffold: wrote {pp(out)}")
    plain = ("no specimen, a minimal 16:9 page (a slide is 1920x1080 and the portrait specimens do not fit; assets/directions/slide-16x9.html is a layout to borrow)" if med == "slide" else
             "no specimen, so this page is a plain start on the palette roles and the dealt type, not the direction's look (build it from references/directions.md)")
    layouts = load("structures").get("layouts", {})
    start = (f'a composition start, not the specimen: page 1 is laid out as "{g["layout_rhythm"][0]}" ({layouts.get(g["layout_rhythm"][0], "").rstrip(".")}). '
             f'Read {pp(spec)} for the rules of its grammar, leave its frame: {d.get("frame", "")}') if composed else None
    print(f"  {direction}: {start or ('specimen ' + spec.name if spec else plain)}; {pages} page(s) at {w}x{h}; hook marker {hook}")
    if med == "video" and not (spec and spec.name.endswith(".motion.html")):
        print("  this page is still: animate it with CSS keyframes or window.seek(t), as assets/directions/departure-board.motion.html does")
        print(f"  for a drawn film (objects, a camera, springs, a film finish under the words): ART.film, {pp(SKILL / 'references' / 'art-motion.md')}")
    print("  links: all absolute (file:///)" + (f"; NOT FOUND, left as they were: {', '.join(missing)}" if missing else ""))
    print("  palette.css: " + (f"linked ({pp(pal)}); " + (f"the {'page and the direction' if composed else 'specimen'}'s colour tokens follow its --ground, --text, --text-2 and --accent" if roles else "the minimal page uses its --ground, --text, --text-2 and --accent") if pal else f"not found next to the page. Make it, then run scaffold again with --force:\n    {palette_cmd(g, piece.get('brand'))}"))
    have = max(map(int, re.findall(r"\.pg-(\d+)", pal.read_text(encoding="utf-8"))), default=0) if pal else pages
    if have < pages:
        print(f"  palette.css has {have} page(s) and the piece has {pages}: the extra pages have no colour. Run palette.py again with --pages {pages}:\n    {palette_cmd(g, piece.get('brand'))}")
    if brand:
        print(f"  brand: {pp(brand)}" + (" linked after tokens.css" if brand.is_file() else " NOT FOUND: the page keeps the neutral default palette of tokens.css"))
    if logo:
        print("  " + logo)
    if kept:
        print("  type: the brand file's faces are kept")
    if fams or not kept:
        print(f"  type {g['type']}: " + ("the direction is built on the house type's width axis (Archivo), so the page keeps it" if keeps else
              f"display {disp}, text {text}, mono {mono}; library.css linked and {', '.join('--' + k for k in fams)} set on :root" if local else
              f"display {disp}, text {text}: NOT local, so the page keeps the house type. Run get_font.py for each family, then set --disp and --body yourself"))
    if med == "video":
        print("  next, the film, then the audit the visual grade also needs:")
        print(f"    node {tool('motion.mjs')} {q(out)} --seconds 8 --sub 2 --poster 7")
        print("    " + render_cmd(out, med))
    else:
        print("  next (it writes audit.json and page-NN.png next to the page; add --pdf for carousel.pdf):")
        print("    " + render_cmd(out, med))
    return 0


def cmd_coverage(a):
    hist = history()
    regs, fams = list(load("registers")), sorted({o["family"] for o in load("operators")})
    grounds = ["dark", "paper", "field"]
    cells = {(h["genome"].get("register"), h["genome"].get("operator_family"), h["genome"].get("ground")) for h in hist if h.get("genome")}
    total = len(regs) * len(fams) * len(grounds)
    print(f"{len(hist)} pieces in memory. Creative space: {len(cells)} of {total} cells used ({100 * len(cells) / total:.1f}%), alpha {alpha(len(hist)):.2f}, d_min {2 + int(math.floor(math.log2(1 + len(hist) / 4)))}.")
    for ax in ("format", "direction", "register", "operator", "hook", "close", "harmony", "type"):
        vals = [h["genome"].get(ax) for h in hist if h.get("genome", {}).get(ax)]
        if not vals:
            continue
        counts = {v: vals.count(v) for v in set(vals)}
        ent = -sum((c / len(vals)) * math.log2(c / len(vals)) for c in counts.values())
        top = sorted(counts.items(), key=lambda kv: -kv[1])[:3]
        print(f"  {ax:9} {len(counts)} distinct, entropy {ent:.2f} bits; most used: {', '.join(f'{k} x{v}' for k, v in top)}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="atelier composer: a graded, memory-driven pipeline that makes every piece different on purpose.",
                                 epilog=f"""Minimal run, in order. The scripts are in {pp(SCRIPTS)}. From a project folder, run them by full path, for example:
  {PY} {q(SELF)} next <slug>
  1. compose.py new <slug> --topic "..."    start a piece (add --scope design when the host system writes the words)
  2. compose.py deal <slug> genome          full scope: pass atoms, lenses and angles first (next says how); design scope: adopt first
  3. compose.py grade <slug> genome ...     the genome worksheet prints the exact line and the notes template
  4. palette.py ...                         the genome worksheet prints the exact line, with the --field-page the layout needs
  5. compose.py scaffold <slug>             the page: a composition start in the dealt direction's type and colours, working links, pages and size set
  6. render.mjs visual.html --audit         build the page, render it, audit it
  7. compose.py deliver <slug>              write the piece to memory (.atelier/history.jsonl)
Quick path (one image, four stages: atoms, angles, genome, visual; only the visual needs a critic):
  compose.py new <slug> --topic "..." --scope quick --medium image [--brand tokens.css]
  compose.py grade <slug> atoms ... --by self                      3 to 5 atoms
  compose.py deal <slug> angles                                    3 operators: pick ONE, write ONE angle
  compose.py similar <slug> "<your one line>" ; compose.py grade <slug> angles ... --by self ; compose.py choose <slug> angle <n> --text "<your one line>"
  compose.py deal <slug> genome ; compose.py grade <slug> genome ... --by self ; palette.py ... (the genome worksheet prints it)
  compose.py scaffold <slug> ; render.mjs visual.html --audit      writes audit.json and page-NN.png next to the page
  compose.py grade <slug> visual ... --by critic --evidence <art-director-verdict.md> ; compose.py deliver <slug>
Lost? compose.py next <slug> says what to do now and prints the grade command.""", formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="command")

    def add(name, summary):
        return sub.add_parser(name, help=summary, description=summary)
    p = add("new", "start a piece and write its worksheets"); p.add_argument("slug"); p.add_argument("--topic", required=True); p.add_argument("--brand", help="the brand's tokens.css: the palette line the genome prints passes it to palette.py --brand, and scaffold links it right after tokens.css. its --logo: url(file) (--logo-on-dark on a dark or colour-field ground) is the only logo a scaffolded page keeps"); p.add_argument("--medium", default="carousel", choices=["carousel", "image", "video", "text", "slide"]); p.add_argument("--scope", default="full", choices=["full", "design", "quick"], help="design: the host system writes, critiques and approves; the composer deals the design and remembers it. quick: one image in four stages (atoms, angles, genome, visual); only the visual needs a critic")
    p = add("next", "say what to do now (always start here)"); p.add_argument("slug")
    p = add("deal", "deal lenses, angles or the genome (a new deal excludes what was tried)"); p.add_argument("slug"); p.add_argument("stage", choices=["lenses", "angles", "genome"]); p.add_argument("--seed", type=int); p.add_argument("--any-type", action="store_true", help="genome: also deal type from taste-skill's library (default: only the local font pairings, whose fonts ship with the skill)"); p.add_argument("--pin", default="", help="genome: axis=value,... fixed before the deal, e.g. register=warmth; the rest is dealt around it and later deals keep it")
    p = add("choose", "record which graded angle wins"); p.add_argument("slug"); p.add_argument("what", choices=["angle"]); p.add_argument("n"); p.add_argument("--text", default="", help="the winner's one line")
    p = add("grade", "grade a stage: scores, notes, and for critic stages the critic's verdict file"); p.add_argument("slug"); p.add_argument("stage", choices=STAGES); p.add_argument("--scores", required=True, help='"criterion=8,criterion=9,..."'); p.add_argument("--notes", help='file with one "criterion: reason" line (25+ characters) per criterion'); p.add_argument("--by", choices=["self", "critic"], default="self"); p.add_argument("--evidence", help="the critic's verdict file: 200+ characters, a verdict or score line, not the notes file (required for critic stages). A FAIL or REVISE verdict cannot pass; scores or a total in it must equal --scores"); p.add_argument("--swap", choices=["pass", "fail"], default="pass"); p.add_argument("--folder", help="visual stage, for a page built without scaffold: the folder with visual.html and its render (audit.json, page-NN.png). A scaffolded page is graded in the folder scaffold wrote it into")
    p = add("adopt", "design scope: adopt an angle the host system has already graded"); p.add_argument("slug"); p.add_argument("--angle", required=True); p.add_argument("--operator", required=True); p.add_argument("--evidence", required=True, help="the host's grading record: 200+ characters, a verdict or score line, and the angle (6+ words in a row) or a winner or PASS line; a record whose only verdict is FAIL or REVISE is refused"); p.add_argument("--pin", default="", help="axis=value,... decided by the host, e.g. direction=receipt,register=dry")
    p = add("similar", "novelty of one line against everything made before"); p.add_argument("slug"); p.add_argument("text")
    p = add("status", "show every stage with its attempts and last grade"); p.add_argument("slug")
    p = add("scaffold", "start the page: a composition start on the grid for each dealt layout word (a film starts from the motion specimen), with working links"); p.add_argument("slug"); p.add_argument("--out", default="visual.html", help="the page to write (default ./visual.html)"); p.add_argument("--force", action="store_true", help="overwrite the page if it exists")
    p = add("deliver", "write the finished piece to memory (.atelier/history.jsonl)"); p.add_argument("slug")
    add("coverage", "how much of the creative space the memory has used")
    a = ap.parse_args()
    if getattr(a, "slug", None) is not None:
        check_slug(a.slug)
    return {"new": cmd_new, "next": cmd_next, "deal": cmd_deal, "choose": cmd_choose, "adopt": cmd_adopt, "grade": cmd_grade, "similar": cmd_similar,
            "status": cmd_status, "scaffold": cmd_scaffold, "deliver": cmd_deliver, "coverage": cmd_coverage}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
