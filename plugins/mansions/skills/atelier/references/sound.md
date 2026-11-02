# Sound: films with a sound track

Most feeds play a film muted, so the film must work without sound first (references/motion.md). Sound is a second layer: it lands each beat for a viewer who turns it on. Worked example: examples/the-run (12 s, 4:5, a code-made sound bed and ten effect cues on nine beats, sample sound).

## What may go in
- Local only. No network call, no model download, no paid service, no generated voice.
- Voice and music are files the user supplies, with a licence that allows the use (credit them in the post text). Atelier ships no voice and no music.
- Effects come only from the Python standard library (`sound.py`: tick, thump, whoosh, rise, chime) or from ffmpeg's own generators (the sound bed: a chord from `aevalsrc`, low-passed, with a slow swell). Label a code-made bed as sample sound when it stands in for real music.

## One timeline drives picture and sound
`timeline.json` sits next to motion.html. Times are in seconds; file paths are relative to the timeline.
```
{"seconds": 12,
 "beats": [{"id": "hook", "at": 0}, {"id": "turn", "at": 3.2}, {"id": "pass", "at": 9.0}],
 "sound": {"target_lufs": -14, "true_peak_db": -1.0,
           "bed":   {"chord_hz": [110, 164.81, 220], "gain_db": -20, "fade_in": 0.3, "fade_out": 2.0},
           "music": {"file": "music.wav", "gain_db": -16, "duck_db": 8, "start": 0, "end": 12},
           "voice": [{"file": "voice/01.wav", "at": 0.3, "text": "Three numbers decide the week."}],
           "cues":  [{"beat": "turn", "fx": "tick", "gain_db": -8}, {"beat": "pass", "fx": "chime", "offset": 0.05}]}}
```
- **Picture.** `motion.mjs` reads the timeline. Each beat becomes a CSS variable `--beat-<id>` on the root (write `animation-delay: var(--beat-turn)`) and `window.TIMELINE` (read it in `window.seek`). The film's length defaults to `"seconds"`. `render.mjs --audit` reads the same timeline: it sets the beats and `window.TIMELINE` as motion.mjs does and checks the film to the timeline's length.
- **Grade.** `video_check.py` writes `video_check.json` with the sha256 of the video it checked. `compose.py grade` takes a film's visual stage only when that file has no FAIL and matches the video.mp4 in the folder.
- **Sound.** `sound.py` places each cue on its beat (or at `"at"`), each voice line at its time, and the bed or music under them. Music and bed duck under a voice (a sidechain compressor keyed by the voice).
- **Words.** Each voice line's `"text"` becomes a caption from its start, held its reading time even after the voice ends, and cut 0.05 s before the next line.
Move a beat in one place and the picture, the effect and the caption move together.

## Run it
```
node S/scripts/motion.mjs motion.html --sub 2 --poster 10      # picture, timed by timeline.json
python S/scripts/sound.py <folder>                              # sound track, loudness, captions
python S/scripts/video_check.py <folder>                        # picture and sound checks
```
`sound.py` copies the picture without re-encoding it, adds an AAC track (192 kb/s, 48 kHz), strips container metadata (`-map_metadata -1 -fflags +bitexact`), and writes captions.json, captions.srt (for platforms) and captions.vtt (for a web page's `<track>`) when the timeline has voice lines. A second run gives the same track, byte for byte.

## Loudness
Two passes of ffmpeg's `loudnorm`: the first measures, the second corrects with the measured values, linearly when the peak allows it and with loudnorm's limiter when it does not. The target is -14 LUFS integrated. That is a common target for social and streaming video, not a standard; broadcast uses -23 LUFS (EBU R 128). The measure is ITU-R BS.1770, as ffmpeg's `loudnorm` and `ebur128` filters implement it. The true peak aims 0.5 dB under the limit (default -1.0 dBTP, a common ceiling for lossy delivery), because the AAC encoder can add a little peak. Set `target_lufs` and `true_peak_db` in the timeline when a platform asks for other values.

## The checks (video_check.py)
They run when the folder's timeline.json has a `"sound"` section. Each has a planted film in tests/test_audio.py that fails it.

| Check | Fails when | Kind |
|---|---|---|
| track | the timeline declares sound and video.mp4 has no sound track | measured |
| length | the sound track and the picture differ by more than 0.1 s | measured |
| loudness | integrated loudness is more than 1 LU from the target | measured (BS.1770); the target is a common choice |
| true peak | the true peak is over the limit | measured (BS.1770, 4 times oversampled) |
| clipping | 3 or more samples in a row at digital full scale, in any channel of the decoded track | measured; the run of 3 is this tool's rule |
| silence at the start | nothing above -50 dBFS for the first 1.0 s or more | measured; the 1.0 s and -50 dBFS are this tool's choice |
| captions | a voice line has no caption with its words starting within 0.3 s, or there is no captions.json | measured |
| reading time | a caption is shorter than its reading time (0.3 s a word, at least 1.2 s) | measured; the rule is references/motion.md's |

A clipped track also breaks the true peak, and usually the loudness: one fault, three lines.

## Directing sound
- One hit per beat at most, on the frame the picture lands; a lead-in (a whoosh or a rise) may run into it. A sound for every move is noise.
- The heaviest picture beat gets the heaviest sound (a thump), the payoff the brightest (a chime), and nothing else that loud.
- A rise ends on its beat; it never starts on it.
- The bed sits well under the cues (about 12 dB in the example) and fades out over the final hold; the film ends on the hold, not on a fade to silence.
- The sound starts at once: frame 0 already carries the hook, and a viewer who turns the sound on should hear the film, not a gap.

## Not measured here
- Whether the sound fits the brand or the picture's mood: the art-director judges the picture only.
- Speech clarity, music licences and the timing of a cue against the picture's motion (the timeline sets the times; nothing listens for them).
- How a platform plays it back: platforms set their own loudness and may re-encode.
