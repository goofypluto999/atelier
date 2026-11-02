#!/usr/bin/env python3
"""Tests for films with sound (1.4.0): scripts/sound.py and the sound checks in scripts/video_check.py. python tests/test_audio.py

1. sound.py makes the planted film's sound from tests/fixtures/s1-sound/timeline.json: a code-made bed, five effect cues
   placed on beats, two voice lines. The voice files are stand-in tones the test makes with ffmpeg's aevalsrc (no voice is
   bundled). The film passes video_check.py, its captions.json, captions.srt and captions.vtt hold one line per voice line,
   and a second run gives the same sound track, byte for byte.
2. Thirteen planted films, each made from the good one, fail their own sound check:
   no track, a track 1 s short, 4 dB too quiet, a true peak over the limit, clipping, 1.5 s of silence at the start,
   voice lines without captions.json, and a voice caption held under its reading time. A clipped track also breaks the
   true peak and the loudness target, so that film must fail those three. No planted film may fail anything else.
   Five more sit just past a threshold or test the caption match line by line: a track 0.3 s short (limit 0.1 s),
   1.3 LU under the target, set from the good film's measured loudness (limit 1 LU), 1.2 s of silence at the start (limit 1.0 s), a voice caption 0.5 s late (limit
   0.3 s), and a caption whose words differ from its voice line.
   The clipping rule's own edge, on a lossless WAV (AAC would smear single samples): a run of 2 samples at full scale is
   not counted, a run of 3 is, in either channel and at either sign.
3. motion.mjs takes the picture's timing from tests/fixtures/s2-beats/timeline.json: the beat "show" becomes --beat-show,
   window.TIMELINE reaches window.seek, and the film's length comes from the timeline.
Steps 1 and 2 need ffmpeg; step 3 also needs node and Playwright. Without them a step prints SKIP and the test passes."""
import array
import importlib.util
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import wave

SKILL = pathlib.Path(__file__).resolve().parent.parent
FIX = SKILL / "tests" / "fixtures"
SOUND = SKILL / "scripts" / "sound.py"
VIDEO_CHECK = SKILL / "scripts" / "video_check.py"
MOTION = SKILL / "scripts" / "motion.mjs"
SECONDS = 8.0
problems = []


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kw)


def ffmpeg(*args):
    r = sh(["ffmpeg", "-hide_banner", "-nostats", "-y", *args])
    if r.returncode:
        raise SystemExit(f"ffmpeg failed: {r.stderr[-800:]}")


def expect(cond, msg):
    print(("ok    " if cond else "FAIL  ") + msg)
    if not cond:
        problems.append(msg)


KINDS = [   # how each FAIL line of video_check.py is named here; a line that matches none is "other"
    ("track", "no sound track"),
    ("length", "sound track is"),
    ("loudness", "loudness "),
    ("peak", "true peak "),
    ("clip", "clipping:"),
    ("silence", "silence at the start"),
    ("captions", "no captions.json"),
    ("captions", "has no caption"),
    ("reading", "is on screen"),
]


def fails_of(folder):
    r = sh([sys.executable, str(VIDEO_CHECK), str(folder)])
    kinds = set()
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("FAIL "):
            kinds.add(next((k for k, key in KINDS if key in line), "other"))
    return r.returncode, kinds, r.stdout


def remux(good, out, audio_filter=None, extra_input=None):
    """The good film's picture with its sound changed by one filter (or mixed with one extra lavfi input)."""
    out.mkdir()
    shutil.copy(good / "timeline.json", out / "timeline.json")
    shutil.copy(good / "captions.json", out / "captions.json")
    args = ["-i", str(good / "video.mp4")]
    if extra_input:
        args += ["-f", "lavfi", "-i", extra_input, "-filter_complex", "[0:a][1:a]amix=inputs=2:normalize=0:duration=first[a]",
                 "-map", "0:v", "-map", "[a]"]
    else:
        args += ["-map", "0:v", "-map", "0:a", "-af", audio_filter]
    ffmpeg(*args, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-map_metadata", "-1", "-fflags", "+bitexact",
           str(out / "video.mp4"))
    return out


def audio_md5(video):
    return sh(["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:a", "-c", "copy", "-f", "md5", "-"]).stdout.strip()


def build_good(tmp):
    good = tmp / "good"
    good.mkdir()
    shutil.copy(FIX / "s1-sound" / "timeline.json", good / "timeline.json")
    # the picture: ffmpeg's moving test pattern, 8 s, no sound (as motion.mjs writes it)
    ffmpeg("-f", "lavfi", "-i", f"testsrc2=s=320x240:r=30:d={SECONDS}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-fflags", "+bitexact", "-map_metadata", "-1", str(good / "video.mp4"))
    shutil.copy(good / "video.mp4", tmp / "silent.mp4")
    # stand-in voice lines: a 180 Hz tone with a syllable-like 4 Hz swell (a test signal, not a voice)
    for name, secs in (("voice-1.wav", 2.0), ("voice-2.wav", 1.6)):
        ffmpeg("-f", "lavfi", "-i", f"aevalsrc='0.5*sin(2*PI*180*t)*(0.55+0.45*sin(2*PI*4*t))':s=48000:d={secs}", str(good / name))
    r = sh([sys.executable, str(SOUND), str(good)])
    print("      " + r.stdout.strip().splitlines()[0] if r.stdout.strip() else r.stderr[-600:])
    return good, r.returncode


def main():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("SKIP  ffmpeg not found: steps 1 to 3 need it")
        return 0
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        good, code = build_good(tmp)
        expect(code == 0, "1. sound.py exits 0 on the planted film")
        code, kinds, out = fails_of(good)
        expect(code == 0 and not kinds, f"1. the good film passes every check (exit {code}, fails {sorted(kinds) or 'none'})")
        if code:
            print(out)
        m = re.search(r"sound: (-?[\d.]+) LUFS", out)
        loud = float(m.group(1)) if m else -14.0   # the good film's measured loudness: the near-miss below is set from it
        caps = json.loads((good / "captions.json").read_text(encoding="utf-8"))
        expect([c["text"] for c in caps] == ["Every film gets the same checks.", "Sound is measured too."]
               and caps[0]["start"] == 0.3 and caps[1]["start"] == 3.0, "1. captions.json holds the two voice lines at their times")
        srt = (good / "captions.srt").read_text(encoding="utf-8")
        vtt = (good / "captions.vtt").read_text(encoding="utf-8")
        expect(srt.startswith("1\n00:00:00,300 --> ") and vtt.startswith("WEBVTT") and vtt.count(" --> ") == 2,
               "1. captions.srt and captions.vtt are written")
        first = audio_md5(good / "video.mp4")
        again = tmp / "again"
        shutil.copytree(good, again)
        shutil.copy(tmp / "silent.mp4", again / "video.mp4")
        sh([sys.executable, str(SOUND), str(again)])
        expect(first and first == audio_md5(again / "video.mp4"), "1. a second run gives the same sound track")

        planted = {
            "no-track": (None, {"track"}),
            "short": ("atrim=0:7.0", {"length"}),
            "quiet": ("volume=-4dB", {"loudness"}),
            "hot-peak": ("extra", {"peak"}),
            "clipped": ("volume=10dB", {"clip", "peak", "loudness"}),
            "late-start": ("adelay=1500|1500,atrim=0:8", {"silence"}),
            "no-captions": (None, {"captions"}),
            "brief-caption": (None, {"reading"}),
            "short-0.3": ("atrim=0:7.7", {"length"}),
            "a-bit-quiet": (f"volume={-15.3 - loud:.2f}dB", {"loudness"}),   # lands at -15.3 LUFS, 1.3 LU under
            "late-start-1.2": ("adelay=1200|1200,atrim=0:8", {"silence"}),
            "late-caption": (None, {"captions"}),
            "wrong-words": (None, {"captions"}),
        }
        for name, (filt, want) in planted.items():
            folder = tmp / name
            if name == "no-track":
                folder.mkdir()
                for f in ("timeline.json", "captions.json"):
                    shutil.copy(good / f, folder / f)
                shutil.copy(tmp / "silent.mp4", folder / "video.mp4")
            elif name == "hot-peak":   # a 40 ms tone at -0.5 dBFS where the mix is quiet (7 s): the peak, not the loudness
                remux(good, folder, extra_input="aevalsrc='0.944*sin(2*PI*1000*t)*between(t,7,7.04)*sin(PI*(t-7)/0.04)'"
                                                 ":s=48000:d=8:c=stereo")
            elif name in ("no-captions", "brief-caption", "late-caption", "wrong-words"):
                shutil.copytree(good, folder)
                if name == "no-captions":
                    (folder / "captions.json").unlink()
                else:
                    c = json.loads((folder / "captions.json").read_text(encoding="utf-8"))
                    if name == "brief-caption":
                        c[0]["end"] = c[0]["start"] + 1.0     # six words need 1.8 s
                    elif name == "late-caption":            # the second line, so the first caption still starts by 0.5 s
                        c[1]["start"] += 0.5
                        c[1]["end"] += 0.5
                    else:
                        c[0]["text"] = "Every film gets the same check."
                    (folder / "captions.json").write_text(json.dumps(c), encoding="utf-8")
            else:
                remux(good, folder, audio_filter=filt)
            code, kinds, out = fails_of(folder)
            expect(code == 1 and kinds == want, f"2. {name}: fails {sorted(kinds)}, expected {sorted(want)}")
            if kinds != want:
                print("\n".join("      " + l for l in out.splitlines() if "FAIL" in l or "sound:" in l))

        # the clipping rule's edge: a quiet stereo tone with runs of full-scale samples planted exactly
        spec = importlib.util.spec_from_file_location("video_check", VIDEO_CHECK)
        vc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vc)
        for name, runs, want in (("clip-2", [(0, 2, 32767)], 0), ("clip-3", [(0, 3, 32767)], 1),
                                 ("clip-3-low", [(1, 3, -32768)], 1), ("clip-2-and-3", [(0, 2, 32767), (1, 3, 32767)], 1)):
            pcm = array.array("h", (int(3000 * math.sin(2 * math.pi * 440 * i / 48000)) for i in range(48000) for _ in (0, 1)))
            for ch, n, v in runs:
                for i in range(n):
                    pcm[2 * (24000 + i) + ch] = v
            if sys.byteorder == "big":
                pcm.byteswap()
            with wave.open(str(tmp / f"{name}.wav"), "wb") as w:
                w.setnchannels(2)
                w.setsampwidth(2)
                w.setframerate(48000)
                w.writeframes(pcm.tobytes())
            got = vc.full_scale_runs(tmp / f"{name}.wav", 2)
            expect(got == want, f"2. {name}: {got} clipped run(s) counted, expected {want}")

    if not shutil.which("node"):
        print("SKIP  3. node not found")
    else:
        with tempfile.TemporaryDirectory() as t:
            out = pathlib.Path(t)
            r = sh(["node", str(MOTION), str(FIX / "s2-beats" / "motion.html"), "--fps", "10", "--size", "320x240", "--out", str(out)])
            if r.returncode == 2 and "Playwright not found" in (r.stderr + r.stdout):
                print("SKIP  3. Playwright not found")
            else:
                expect(r.returncode == 0, f"3. motion.mjs renders the beat fixture (exit {r.returncode})")
                texts = {x["id"]: x for x in json.loads((out / "texts.json").read_text(encoding="utf-8"))["texts"]} if r.returncode == 0 else {}
                dur = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out / "video.mp4")]).stdout.strip()
                expect(abs(float(dur or 0) - 4.0) < 0.05, f"3. the film's length comes from the timeline (4 s, got {dur} s)")
                w = texts.get("word", {})
                expect(abs(w.get("start", 99) - 1.0) <= 0.15, f"3. --beat-show times the picture (word whole from {w.get('start')} s, beat 1.0 s)")
                expect(texts.get("count", {}).get("text") == "beats 1", "3. window.TIMELINE reaches window.seek")
                expect((out / "timeline.json").exists(), "3. timeline.json is copied next to the film for sound.py")
                # the audit reads the same timeline: 4 s from it, so the hard rules run again every half second to 3.5 s (without it the
                # page's CSS ends at 3.1 s, the beat's 3 s fallback plus its 0.1 s fade, and the last check would be at 3 s). The page's
                # seek throws without window.TIMELINE or --beat-show, and the audit would print that as a FAIL.
                a = sh(["node", str(SKILL / "scripts" / "render.mjs"), str(FIX / "s2-beats" / "motion.html"), "--audit", "--size", "320x240",
                        "--no-png", "--out", str(out / "audit")])
                m = re.search(r"hard rules checked again at ([\d., s]+)", a.stdout)
                at = [float(x) for x in re.findall(r"[\d.]+", m.group(1))] if m else []
                expect(at and max(at) == 3.5, f"3. render.mjs --audit takes the film's length from timeline.json (checked at {at})")
                expect("threw" not in a.stdout, "3. render.mjs --audit sets window.TIMELINE and --beat-show before it seeks"
                       + ("" if "threw" not in a.stdout else ": " + next(l for l in a.stdout.splitlines() if "threw" in l).strip()))

    print("PASS" if not problems else f"FAIL {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
