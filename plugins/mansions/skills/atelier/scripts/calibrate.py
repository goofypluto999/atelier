#!/usr/bin/env python3
"""Calibrate a critic against known answers before trusting it (references/critique.md).

  python calibrate.py prepare [--set <skill>/evals/anchors] [--out .atelier/calibration]
  python calibrate.py score <out>/<date>/verdicts.json [--set ...]

prepare: shuffles the set's images (or .md texts) into <out>/<date>/01.png, 02.png ... and a map.json the critic
must NOT see. Give the critic only the NN files. score: compares the critic's verdicts with labels.json:
every flawed item must FAIL naming at least one of its labelled flaws, every good item must PASS. Appends the
result to <out>/calibration.csv. A FAIL means the critic is not trusted until its prompt or model is fixed.
Never edit labels.json to make a run pass. Standard library only.
"""
import argparse
import csv
import datetime as dt
import json
import pathlib
import random
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
DEFAULT_SET = pathlib.Path(__file__).resolve().parent.parent / "evals" / "anchors"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "score"])
    ap.add_argument("verdicts", nargs="?")
    ap.add_argument("--set", default=str(DEFAULT_SET))
    ap.add_argument("--out", default=".atelier/calibration")
    a = ap.parse_args()
    s = pathlib.Path(a.set)
    labels = {k: v for k, v in json.loads((s / "labels.json").read_text(encoding="utf-8")).items() if not k.startswith("_")}
    if a.cmd == "prepare":
        day = dt.date.today().isoformat()
        run = pathlib.Path(a.out) / day
        if run.exists():
            shutil.rmtree(run)
        run.mkdir(parents=True)
        items = sorted(labels)
        random.Random(day).shuffle(items)
        mapping = {}
        for i, item in enumerate(items, 1):
            src = next((s / f"{item}{ext}" for ext in (".png", ".md", ".txt") if (s / f"{item}{ext}").exists()), None)
            if not src:
                print(f"missing file for {item}")
                return 1
            n = f"{i:02d}"
            shutil.copy(src, run / f"{n}{src.suffix}")
            mapping[n] = item
        (run / "map.json").write_text(json.dumps(mapping, indent=1), encoding="utf-8")
        print(f"{len(items)} items in {run}. Give the critic ONLY the NN files, then save its JSON as {run / 'verdicts.json'}.")
        return 0
    vpath = pathlib.Path(a.verdicts)
    verdicts = json.loads(vpath.read_text(encoding="utf-8"))
    mapping = json.loads((vpath.parent / "map.json").read_text(encoding="utf-8"))
    misses, alarms, caught, clean = [], [], 0, 0
    for n, item in mapping.items():
        v = verdicts.get(n, {"verdict": "MISSING"})
        named = set(v.get("flaws", []) or v.get("sins", []))
        if labels[item]:
            if v.get("verdict") == "FAIL" and named & set(labels[item]):
                caught += 1
            else:
                misses.append(f"{n} ({item}): expected FAIL with one of {labels[item]}, got {v.get('verdict')} {sorted(named)}")
        elif v.get("verdict") == "PASS":
            clean += 1
        else:
            alarms.append(f"{n} ({item}): good item judged {v.get('verdict')} {sorted(named)}")
    bad_n = sum(1 for i in mapping.values() if labels[i])
    result = "PASS" if not misses and not alarms else "FAIL"
    print(f"calibration {result}: caught {caught}/{bad_n} flawed items, passed {clean}/{len(mapping) - bad_n} good items")
    for m in misses + alarms:
        print("  ", m)
    log = vpath.parent.parent / "calibration.csv"
    new = not log.exists()
    with log.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["date", "set", "result", "caught", "flawed", "clean", "good", "notes"])
        w.writerow([vpath.parent.name, s.name, result, caught, bad_n, clean, len(mapping) - bad_n, "; ".join(misses + alarms)[:400]])
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
