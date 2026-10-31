#!/usr/bin/env python3
"""Copy lint for words that sit on or under a design: headlines, page text, captions, post text.

  python copy_lint.py <file.md|file.txt|visual.html|captions.json> [--no-dashes] [--max-you 3] [--brand "Name"] [--allow "word word"]

Fails (exit 1) on the five sins' obvious patterns (copy_patterns.json: preachy, salesy, cringe, slop, plus stock
words) and on flat rhythm: when every sentence has about the same length, text reads generated. Human writing
measured in our tests had a sentence-length coefficient of variation of 0.49 to 1.14; flat AI-like drafts 0.22
to 0.39. The floor is 0.40 for prose of 6 sentences or more (.md and .txt; --rhythm for HTML or captions, where table cells and labels would skew it). The patterns catch the obvious; references/critique.md
has the reviewer that catches the rest. Standard library only.

Warns (never fails) on crutch words: a content word that appears 3 or more times across a set of pages, or twice on one page
(4 or more times in a single page, post or caption: a short piece keeps its subject's nouns). Not counted: stop words and words
under 4 letters; the brand (--brand); the words you pass with --allow (the subject's own terms); the page <title>; the words of
the cover headline (data-role="hook" on page 1); a word in a page's own headline when it is repeated on that page; the unit
after a number ("15 hours"); ALL-CAPS labels (WHEN, ITEM); fine print (data-role="fine"); logos; SVG labels; and short rows of a
repeated structure (a table, a ticket rail). The thresholds and the stop words are in copy_patterns.json.
"""
import argparse
import html
import json
import pathlib
import re
import sys
from collections import Counter
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
HERE = pathlib.Path(__file__).resolve().parent


def text_of(path):
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        try:
            data = json.loads(raw)
            return "\n".join(c.get("text", "") for c in data) if isinstance(data, list) else raw
        except ValueError:
            return raw
    if path.suffix in {".html", ".htm"}:
        raw = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
        raw = re.sub(r"(?s)<!--.*?-->", " ", raw)
        raw = re.sub(r"<br\s*/?>|</(p|div|h\d|li|section)>", "\n", raw, flags=re.I)
        raw = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return raw


_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_HIDDEN = {"script", "style", "head", "noscript", "template", "svg"}


class _Node:
    __slots__ = ("tag", "attrs", "parent", "kids")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.kids = tag, attrs, parent, []


class _Tree(HTMLParser):
    """The page as a small tree, so a row of a repeated structure can be told from prose."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = self.cur = _Node("root", {}, None)
        self.title, self._in_title = [], False

    def handle_starttag(self, tag, attrs):
        self._in_title = self._in_title or tag == "title"
        node = _Node(tag, dict(attrs), self.cur)
        self.cur.kids.append(node)
        if tag not in _VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.kids.append(_Node(tag, dict(attrs), self.cur))

    def handle_endtag(self, tag):
        self._in_title = self._in_title and tag != "title"
        n = self.cur
        while n.parent and n.tag != tag:
            n = n.parent
        if n.parent:
            self.cur = n.parent

    def handle_data(self, data):
        if self._in_title:
            self.title.append(data)
        elif data.strip():
            self.cur.kids.append(data)


def _words_in(node):
    return sum(len(k.split()) if isinstance(k, str) else _words_in(k) for k in node.kids)


def _prose(node, out, hook=False, row=False):
    """Append (text, in_hook) for the words a reader reads as copy: not fine print, logos, hidden or SVG text, nor short rows of a repeated structure."""
    for k in node.kids:
        if isinstance(k, str):
            if not row or hook:
                out.append((k, hook))
            continue
        if k.tag in _HIDDEN or k.attrs.get("data-role") in {"fine", "logo"} or k.attrs.get("aria-hidden") == "true" or "hidden" in k.attrs:
            continue
        sig = (k.tag, k.attrs.get("class") or "")
        same = sum(1 for s in node.kids if not isinstance(s, str) and (s.tag, s.attrs.get("class") or "") == sig)
        is_row = same >= 3 and (sig[1] or k.tag in {"li", "tr", "td", "dt", "dd"}) and _words_in(k) < 12
        _prose(k, out, hook or k.attrs.get("data-role") == "hook", row or is_row)


def pages_of(path):
    """(pages, title words): each page a list of (text, in_hook). HTML splits on section.page, captions.json on its items, anything else is one page."""
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [[(c.get("text", ""), False)] for c in data if isinstance(c, dict)], []
        except ValueError:
            pass
    if path.suffix in {".html", ".htm"}:
        tree = _Tree()
        tree.feed(raw)
        secs = []

        def find(n):
            for k in n.kids:
                if isinstance(k, str):
                    continue
                if k.tag == "section" and "page" in (k.attrs.get("class") or "").split():
                    secs.append(k)
                else:
                    find(k)

        find(tree.root)
        pages = []
        for s in secs or [tree.root]:
            out = []
            _prose(s, out)
            pages.append(out)
        return pages, tree.title
    return [[(raw, False)]], []


def stem(w):
    for suf in ("ingly", "edly", "ing", "ed", "es", "s", "ly"):
        if w.endswith(suf) and len(w) - len(suf) >= 3 and not (suf == "s" and w.endswith(("ss", "us", "is"))):
            w = w[: -len(suf)]
            break
    return w[:-1] if w.endswith("e") and len(w) > 3 else w


_NUMBER_WORDS = set("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million half dozen".split())


def content_words(text, stop, label_ok=False):
    """(stem, word) for every content word: letters only, 4 or more of them, not a stop word or a contraction. Not counted: the unit after a number
    ("15 hours", "twenty minutes": the unit repeats because the numbers are different) and, unless label_ok, a word in an ALL-CAPS label (WHEN, ITEM, HOURS)."""
    out, prev = [], ""
    for m in re.finditer(r"[A-Za-z0-9][A-Za-z0-9'’]*", text):
        tok = m.group(0)
        w = tok.lower().replace("’", "'")
        w = w[:-2] if w.endswith("'s") else w
        unit = bool(re.search(r"\d", prev)) or prev in _NUMBER_WORDS
        prev = w
        if len(w) < 4 or "'" in w or w in stop or re.search(r"\d", w) or unit:
            continue
        if tok.isupper() and not label_ok:
            continue
        st = stem(w)
        if st not in stop:
            out.append((st, w))
    return out


def repeat_warning(pages, title, pats, brand="", allow=""):
    """One warning naming the crutch words, or None. See the module doc for the rule and what is not counted."""
    rule = {"across": 3, "on_page": 2, "single": 4, **pats.get("repeat_rule", {})}
    stop = set(pats.get("repeat_stop", []))
    skip = {s for s, _ in content_words(" ".join([brand, allow, *title]), set(), True)} | {w.lower() for w in re.findall(r"[A-Za-z]+", allow)}
    per, hooked, shown = [], [], {}
    for page in pages:
        c, h = Counter(), set()
        for text, in_hook in page:
            for s, w in content_words(text, stop, in_hook):
                if s in skip:
                    continue
                c[s] += 1
                shown.setdefault(s, Counter())[w] += 1
                if in_hook:
                    h.add(s)
        per.append(c)
        hooked.append(h)
    total = Counter()
    for c in per:
        total.update(c)
    hits = []
    for s, n in total.items():
        if s in hooked[0]:   # the cover headline names the subject: its words are the subject's own terms
            continue
        if len(pages) > 1:
            twice = [i + 1 for i, c in enumerate(per) if c[s] >= rule["on_page"] and s not in hooked[i]]
            if n >= rule["across"] or twice:
                hits.append((s, n, [i + 1 for i, c in enumerate(per) if c[s]], twice))
        elif n >= rule["single"]:
            hits.append((s, n, [], []))
    if not hits:
        return None
    hits.sort(key=lambda t: (-t[1], t[0]))
    parts = []
    for s, n, on, twice in hits[:6]:
        form = min(shown[s], key=lambda w: (-shown[s][w], len(w)))
        where = (f" (twice on page {twice[0]})" if twice and n < rule["across"] else f" (pages {', '.join(map(str, on))})") if on else ""
        parts.append(f"{form} x{n}{where}")
    more = f", and {len(hits) - 6} more" if len(hits) > 6 else ""
    return f"repeated words: {', '.join(parts)}{more}; a crutch unless it is the subject's own term (keep it with --allow \"word\")"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--no-dashes", action="store_true", help="fail on any em or en dash (house rule for some brands)")
    ap.add_argument("--max-you", type=int, default=3)
    ap.add_argument("--rhythm", action="store_true", help="check sentence rhythm on HTML or captions too (on by default for .md and .txt prose)")
    ap.add_argument("--brand", default="", help="the brand name: its words are not counted as repeats")
    ap.add_argument("--allow", default="", help="words that are the subject's own terms, not crutches (space or comma separated)")
    a = ap.parse_args()
    pats = json.loads((HERE / "copy_patterns.json").read_text(encoding="utf-8"))
    text = text_of(pathlib.Path(a.file))
    low = text.lower()
    fails, warns = [], []
    for w in pats["words"]:
        if re.search(r"(?<![\w-])" + re.escape(w.lower()) + r"(?![\w-])", low):
            fails.append(f"stock phrase '{w}'")
    for sin in ("preachy", "salesy", "cringe", "slop"):
        for p in pats[sin]:
            m = re.search(p, text, flags=re.I | re.M)
            if m:
                fails.append(f"SIN {sin}: '{m.group(0).strip()}'")
    dashes = text.count(chr(0x2014)) + text.count(chr(0x2013))
    if a.no_dashes and dashes:
        fails.append(f"{dashes} em or en dash(es)")
    elif dashes > 3:
        warns.append(f"{dashes} em or en dashes: a common tell when there are many")
    unquoted = re.sub(r'"[^"]*"', "", text)
    you = len(re.findall(r"\byou(?:r|rs|rself)?\b", unquoted, flags=re.I))
    if you > a.max_you:
        fails.append(f"'you' {you} times: reads as a lecture")
    sents = [s for s in re.split(r"(?<=[.!?])\s+|\n+", re.sub(r"https?://\S+|#\w+", "", text)) if len(s.split()) >= 1]
    lens = [len(s.split()) for s in sents]
    info = {"sentences": len(lens), "words": sum(lens)}
    prose = pathlib.Path(a.file).suffix in {".md", ".txt", ""} or a.rhythm
    if prose and len(lens) >= 6:
        mean = sum(lens) / len(lens)
        cv = (sum((n - mean) ** 2 for n in lens) / len(lens)) ** 0.5 / mean
        info["rhythm_cv"] = round(cv, 2)
        if cv < 0.40:
            fails.append(f"flat rhythm: sentence-length CV {cv:.2f} (needs 0.40 or more)")
    pages, title = pages_of(pathlib.Path(a.file))
    rep = repeat_warning(pages, title, pats, a.brand, a.allow)
    if rep:
        warns.append(rep)
    print(f"== {a.file} {json.dumps(info)}")
    for f in fails:
        print("  FAIL", f)
    for w in warns:
        print("  warn", w)
    print("  PASS" if not fails else "  FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
