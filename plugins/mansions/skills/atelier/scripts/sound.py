#!/usr/bin/env python3
"""Give a rendered film its sound, from the same timeline that timed its picture. Local only: ffmpeg and the Python
standard library. No network, no model, no paid service. Voice and music are files the user supplies; effects and the
optional sound bed are made here (Python standard library and ffmpeg's own aevalsrc generator).

  python sound.py <folder> [--timeline <timeline.json>]

<folder> holds video.mp4 (from motion.mjs) and timeline.json (or pass --timeline). Writes into <folder>:
  video.mp4      the same picture (copied, not re-encoded) with an AAC sound track, metadata stripped
  captions.json  one caption per voice line, from the line's text and times (only when the timeline has voice lines)
  captions.srt   for platforms that take a caption file; captions.vtt for a web page's <track>
Then run video_check.py <folder>: a film whose timeline declares sound gets the sound checks (references/sound.md).

timeline.json (times in seconds; paths relative to the timeline file):
  {"seconds": 12,
   "beats": [{"id": "hook", "at": 0}, {"id": "turn", "at": 3.2}],
   "sound": {"target_lufs": -14, "true_peak_db": -1.0,
             "bed":   {"chord_hz": [110, 164.81, 220], "gain_db": -20, "start": 0, "end": 12, "fade_in": 0.3, "fade_out": 1.5},
             "music": {"file": "music.wav", "gain_db": -16, "duck_db": 8, "start": 0, "fade_in": 0.3, "fade_out": 1.5},
             "voice": [{"file": "voice/01.wav", "at": 0.3, "text": "Three numbers decide the week."}],
             "cues":  [{"beat": "turn", "fx": "tick", "gain_db": -8}, {"at": 9.0, "fx": "chime"}]}}
Effects: tick, thump, whoosh, rise, chime. A cue names a beat (with an optional "offset") or an "at" time.
Loudness: two passes of ffmpeg's loudnorm (ITU-R BS.1770 measurement) to -14 LUFS integrated, a common target for
social and streaming video, not a standard; the true peak aims 0.5 dB under the limit (default -1.0 dBTP), because
the AAC encoder can add a little peak. Exit 1 when a step fails.
"""
import array
import json
import math
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import tempfile
import wave

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

RATE = 48000
TARGET_LUFS = -14.0      # a common target for social and streaming video (references/sound.md); not a standard
TRUE_PEAK_DB = -1.0      # a common ceiling for lossy delivery; the encoder can add a little peak, so loudnorm aims 0.5 dB under
FX = ("tick", "thump", "whoosh", "rise", "chime")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"sound: FAIL {cmd[0]} exited {r.returncode}\n{r.stderr[-1500:]}")
    return r


def stream_seconds(path, kind="v"):
    r = run(["ffprobe", "-v", "error", "-select_streams", f"{kind}:0", "-show_entries", "stream=duration",
             "-of", "csv=p=0", str(path)])
    out = r.stdout.strip().splitlines()
    return float(out[0]) if out and out[0] not in ("", "N/A") else 0.0


def read_time(text, pad=0.0, floor=1.2):
    """The caption reading rule from video_check.py: 0.3 s a word (CJK 4.5 characters a second), at least floor."""
    here = pathlib.Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    try:
        from video_check import read_time as rt
    finally:
        sys.path.pop(0)
    return rt(text, pad, floor)


def beat_times(tl):
    beats = {}
    for b in tl.get("beats", []):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(b.get("id", ""))):
            raise SystemExit(f"sound: FAIL beat id {b.get('id')!r}: use lower case letters, digits and dashes")
        beats[b["id"]] = float(b["at"])
    return beats


def cue_time(cue, beats):
    if "beat" in cue:
        if cue["beat"] not in beats:
            raise SystemExit(f"sound: FAIL cue names beat {cue['beat']!r}, which timeline.json does not list")
        return beats[cue["beat"]] + float(cue.get("offset", 0))
    return float(cue["at"])


# ---- effects, made with the Python standard library (deterministic: the noise has a fixed seed per cue) ----
def fx_samples(kind, seed):
    """Mono samples of one effect at 48 kHz, peak about 1.0, and the offset in seconds of its hit from its first sample."""
    rnd = random.Random(seed)
    out, lead = [], 0.0
    if kind == "tick":                       # a short bright click: 1.8 kHz, 2 ms attack, 14 ms decay
        n = int(0.09 * RATE)
        for i in range(n):
            t = i / RATE
            out.append(min(1.0, t / 0.002) * math.exp(-t / 0.014) * math.sin(2 * math.pi * 1800 * t))
    elif kind == "thump":                    # a low knock: a sine falling from 95 Hz to 45 Hz, 90 ms decay
        n, ph = int(0.45 * RATE), 0.0
        for i in range(n):
            t = i / RATE
            ph += 2 * math.pi * (45 + 50 * math.exp(-t / 0.05)) / RATE
            out.append(min(1.0, t / 0.003) * math.exp(-t / 0.09) * math.sin(ph))
    elif kind == "whoosh":                   # noise through a one-pole low-pass that opens and closes; the hit is its middle
        n, y, lead = int(0.6 * RATE), 0.0, 0.35
        for i in range(n):
            t = i / RATE
            env = math.sin(math.pi * t / 0.6) ** 2
            a = 0.02 + 0.25 * env
            y += a * (rnd.uniform(-1, 1) - y)
            out.append(env * y * 3.0)
    elif kind == "rise":                     # a sine gliding up from 300 Hz to 900 Hz that ends on the cue
        n, ph, lead = int(0.8 * RATE), 0.0, 0.8
        for i in range(n):
            t = i / RATE
            ph += 2 * math.pi * (300 * 3 ** (t / 0.8)) / RATE
            out.append((t / 0.8) ** 2 * math.sin(ph) * (1 - max(0.0, (t - 0.77) / 0.03)))
    elif kind == "chime":                    # three partials (A5, E6, A6) with their own decays
        n = int(1.6 * RATE)
        for i in range(n):
            t = i / RATE
            a = min(1.0, t / 0.004)
            out.append(a * (0.6 * math.exp(-t / 0.7) * math.sin(2 * math.pi * 880 * t)
                            + 0.3 * math.exp(-t / 0.45) * math.sin(2 * math.pi * 1320 * t)
                            + 0.2 * math.exp(-t / 0.3) * math.sin(2 * math.pi * 1760 * t)))
    else:
        raise SystemExit(f"sound: FAIL effect {kind!r}: use one of {', '.join(FX)}")
    peak = max(abs(x) for x in out) or 1.0
    return [x / peak for x in out], lead


def write_fx(path, cues, beats, seconds):
    """All effect cues on one mono track, as 16-bit WAV. Returns the list of (time, effect) placed."""
    n = int(round(seconds * RATE))
    track = array.array("d", bytes(8 * n))
    placed = []
    for k, cue in enumerate(cues):
        at = cue_time(cue, beats)
        samples, lead = fx_samples(cue.get("fx", "tick"), seed=1000 + k)
        gain = 10 ** (float(cue.get("gain_db", -6)) / 20)
        start = int(round((at - lead) * RATE))
        for i, x in enumerate(samples):
            j = start + i
            if 0 <= j < n:
                track[j] += gain * x
        placed.append((round(at, 3), cue.get("fx", "tick")))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(array.array("h", (int(max(-1.0, min(1.0, x)) * 32767) for x in track)).tobytes())
    return placed


def bed_expr(bed):
    """An aevalsrc expression: the chord's sines with a slow swell (ffmpeg's own generator)."""
    hz = [float(f) for f in bed.get("chord_hz", [110, 164.81, 220])]
    tones = "+".join(f"sin(2*PI*{f:.3f}*t)" for f in hz)
    return f"({tones})/{len(hz)}*(0.75+0.25*sin(2*PI*0.125*t))"


def placed_track(label, src, gain_db, start, end, fade_in, fade_out, seconds):
    """Filter text that levels, fades and places one stereo input on the film's clock."""
    start, end = max(0.0, start), min(seconds, end)
    ms = int(round(start * 1000))
    fo_start = max(start, end - fade_out)
    return (f"{src}aresample={RATE},aformat=sample_fmts=fltp:channel_layouts=stereo,volume={gain_db}dB,"
            f"atrim=0:{end - start:.3f},afade=t=in:d={fade_in},afade=t=out:st={fo_start - start:.3f}:d={fade_out},"
            f"adelay={ms}|{ms},apad=whole_dur={seconds:.3f},atrim=0:{seconds:.3f}[{label}]")


def mix(tl, base, video, fx_wav, seconds, out_wav):
    snd = tl["sound"]
    inputs, chains, mains = ["-i", str(fx_wav)], [], []
    chains.append(f"[0:a]aresample={RATE},aformat=sample_fmts=fltp:channel_layouts=stereo,"
                  f"apad=whole_dur={seconds:.3f},atrim=0:{seconds:.3f}[fx]")
    mains.append("[fx]")
    idx = 1
    voices = snd.get("voice", [])
    if voices:
        labels = []
        for k, v in enumerate(voices):
            f = (base / v["file"]).resolve()
            if not f.exists():
                raise SystemExit(f"sound: FAIL voice file {v['file']} not found")
            inputs += ["-i", str(f)]
            vlen = stream_seconds(f, "a")
            chains.append(placed_track(f"v{k}", f"[{idx}:a]", float(v.get("gain_db", 0)), float(v["at"]),
                                       float(v["at"]) + vlen, 0.01, 0.02, seconds))
            labels.append(f"[v{k}]")
            idx += 1
        chains.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,asplit=2[vox][key]")
        mains.append("[vox]")
    under = []
    if "bed" in snd:
        b = snd["bed"]
        inputs += ["-f", "lavfi", "-i", f"aevalsrc='{bed_expr(b)}':s={RATE}:d={seconds:.3f}"]
        chains.append(placed_track("bed", f"[{idx}:a]lowpass=f=1400,", float(b.get("gain_db", -20)), float(b.get("start", 0)),
                                   float(b.get("end", seconds)), float(b.get("fade_in", 0.3)), float(b.get("fade_out", 1.5)), seconds))
        under.append(("bed", b))
        idx += 1
    if "music" in snd:
        m = snd["music"]
        f = (base / m["file"]).resolve()
        if not f.exists():
            raise SystemExit(f"sound: FAIL music file {m['file']} not found")
        inputs += ["-i", str(f)]
        chains.append(placed_track("mus", f"[{idx}:a]", float(m.get("gain_db", -16)), float(m.get("start", 0)),
                                   float(m.get("end", seconds)), float(m.get("fade_in", 0.3)), float(m.get("fade_out", 1.5)), seconds))
        under.append(("mus", m))
        idx += 1
    if under:
        chains.append("".join(f"[{u}]" for u, _ in under) + f"amix=inputs={len(under)}:normalize=0[under]")
        if voices:   # the music and bed step back under the voice: a sidechain compressor keyed by the voice
            duck = max(float(cfg.get("duck_db", 8)) for _, cfg in under)
            ratio = max(2.0, min(20.0, 1 + duck / 3))
            chains.append(f"[under][key]sidechaincompress=threshold=0.03:ratio={ratio:.1f}:attack=20:release=350[ducked]")
            mains.append("[ducked]")
        else:
            mains.append("[under]")
    elif voices:
        chains.append("[key]anullsink")
    chains.append("".join(mains) + f"amix=inputs={len(mains)}:normalize=0,atrim=0:{seconds:.3f}[mix]")
    run(["ffmpeg", "-hide_banner", "-nostats", "-y"] + inputs + ["-filter_complex", ";".join(chains), "-map", "[mix]",
         "-c:a", "pcm_f32le", "-ar", str(RATE), str(out_wav)])


def loudnorm(raw, out, target, peak):
    """Two passes: measure, then correct with the measured values (linear when the peak allows it)."""
    spec = f"I={target}:TP={peak - 0.5}:LRA=11"
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(raw), "-af", f"loudnorm={spec}:print_format=json",
               "-f", "null", "-"]).stderr
    m = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    second = (f"loudnorm={spec}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
              f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=json")
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(raw), "-af", second + f",aresample={RATE}",
               "-c:a", "pcm_f32le", str(out)]).stderr
    m2 = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    return float(m["input_i"]), m2.get("normalization_type", "?")


def captions(voices, base, seconds):
    lines = []
    timed = sorted((float(v["at"]), v) for v in voices if str(v.get("text", "")).strip())
    for k, (at, v) in enumerate(timed):
        vlen = stream_seconds((base / v["file"]).resolve(), "a")
        text = " ".join(str(v["text"]).split())
        end = max(at + vlen, at + read_time(text))           # held at least its reading time, even after the voice ends
        nxt = timed[k + 1][0] if k + 1 < len(timed) else seconds
        lines.append({"start": round(at, 3), "end": round(min(end, nxt - 0.05, seconds), 3), "text": text})
    return lines


def stamp(s, sep):
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d}{sep}{ms % 1000:03d}"


def main(argv):
    if len(argv) < 2 or argv[1].startswith("-"):
        print(__doc__)
        return 2
    folder = pathlib.Path(argv[1]).resolve()
    tl_path = pathlib.Path(argv[argv.index("--timeline") + 1]).resolve() if "--timeline" in argv else folder / "timeline.json"
    video = folder / "video.mp4"
    for need in (tl_path, video):
        if not need.exists():
            print(f"sound: FAIL {need.name} not found in {need.parent.name}/")
            return 1
    if not shutil.which("ffmpeg"):
        print("sound: FAIL ffmpeg not found")
        return 1
    tl = json.loads(tl_path.read_text(encoding="utf-8"))
    if not tl.get("sound"):
        print("sound: FAIL timeline.json has no \"sound\" section")
        return 1
    if tl_path.parent != folder:   # video_check.py reads the declaration next to the film
        shutil.copyfile(tl_path, folder / "timeline.json")
    base, snd = tl_path.parent, tl["sound"]
    seconds = stream_seconds(video, "v")
    target = float(snd.get("target_lufs", TARGET_LUFS))
    peak = float(snd.get("true_peak_db", TRUE_PEAK_DB))
    beats = beat_times(tl)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        placed = write_fx(tmp / "fx.wav", snd.get("cues", []), beats, seconds)
        mix(tl, base, video, tmp / "fx.wav", seconds, tmp / "mix.wav")
        before, kind = loudnorm(tmp / "mix.wav", tmp / "norm.wav", target, peak)
        out = tmp / "video.mp4"
        run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(video), "-i", str(tmp / "norm.wav"),
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", str(RATE),
             "-t", f"{seconds:.3f}", "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact",
             "-movflags", "+faststart", str(out)])
        shutil.move(str(out), str(video))
    lines = captions(snd.get("voice", []), base, seconds)
    if lines:
        (folder / "captions.json").write_text(json.dumps(lines, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        (folder / "captions.srt").write_text("\n".join(f"{i + 1}\n{stamp(c['start'], ',')} --> {stamp(c['end'], ',')}\n{c['text']}\n"
                                                       for i, c in enumerate(lines)), encoding="utf-8")
        (folder / "captions.vtt").write_text("WEBVTT\n\n" + "\n".join(f"{stamp(c['start'], '.')} --> {stamp(c['end'], '.')}\n{c['text']}\n"
                                                                      for c in lines), encoding="utf-8")
    print(f"sound: {video.name} now carries sound ({seconds:.2f} s): {len(placed)} effect cue(s), "
          f"{len(snd.get('voice', []))} voice line(s), {'bed ' if 'bed' in snd else ''}{'music ' if 'music' in snd else ''}"
          f"mixed from {before:.1f} LUFS to a {target:g} LUFS target ({kind} loudnorm, 2 passes)"
          + (f"; {len(lines)} caption(s) in captions.json, captions.srt, captions.vtt" if lines else ""))
    print(f"sound: next, python {pathlib.Path(__file__).with_name('video_check.py').name} {folder.name} (the sound checks run because timeline.json declares sound)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
