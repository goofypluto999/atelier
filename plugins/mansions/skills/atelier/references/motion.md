# Motion: short films made in code

## The render contract
A film is a pure function of time. `window.seek(t)` paints the exact frame for t seconds; a headless browser calls it for every frame and pipes screenshots to ffmpeg (`scripts/motion.mjs`). Because nothing depends on a live clock, every render is identical and any shot can be fixed and re-rendered alone.
- No CSS transitions, no setTimeout or requestAnimationFrame driving the film, no state carried between frames, no Math.random (use the seeded `M.hash` in assets/lib/motion.js).
- CSS @keyframes also work: motion.mjs pauses every animation and sets its time per frame. An element with two animations needs two animation-delay values.
- Wait for fonts (`document.fonts.ready`; motion.mjs does it).
- Motion blur: `--sub 2` to `--sub 4` renders sub-frames and blends them; worth it for fast moves.
- Encode H.264, yuv420p, CRF 16 to 20, `+faststart`. 30 fps is enough for most social pieces.
- The page loads local files only: motion.mjs blocks any other request and fails the render.
- A drawn film (objects on a canvas, a camera that pushes, glides and pulls, springs, a film finish) uses `ART.film` from assets/lib/art-motion.js under the same contract: references/art-motion.md.

Worked examples: assets/directions/departure-board.motion.html (8 s, 4:5, split-flap) and examples/the-dot-reel (10 s, 9:16, a dot on a curve with a rolling counter and a named peak). Both pass video_check.py.

## Springs, not curves
Cheap motion slides from A to B on a fixed curve. Expensive motion has weight: it accelerates, overshoots a hair and settles, which is a damped spring. `M.spring(t, k, d)` in assets/lib/motion.js is closed-form, so any frame can be computed directly. When a value changes target several times (a cursor, a box resizing), add one spring per change (`M.track`), so the motion stays smooth.
- Stiff (k 300 and up) for small parts; soft (k 90 to 140) for big type and objects. Overshoot under 2% for UI, none for type.
- When a curve is needed: ease-out `cubic-bezier(.16,1,.3,1)` for entrances, `cubic-bezier(.76,0,.24,1)` for moves; never ease-in for an entrance. Exits are faster than entrances.
- IBM Carbon's distinction helps: productive motion (fast, 70 to 240 ms, for things that just need to move) versus expressive motion (slower, 240 to 700 ms, for moments that should be noticed). A film is mostly productive with two or three expressive moments.

## The twelve principles (Thomas and Johnston, "The Illusion of Life", 1981), applied to brand motion
Staging (one thing at a time, clearly), anticipation (a small pull back before a big move), follow-through and overlapping action (parts settle at different times: stagger 30 to 110 ms), slow in and slow out (springs do this), arcs (objects travel on curves, not straight diagonals), secondary action (a small supporting move, never competing), timing (weight comes from duration), exaggeration (just enough to read at phone size), squash and stretch (for UI, only a hint), solid drawing (consistent perspective and stroke), appeal (a clear silhouette), straight-ahead versus pose-to-pose (plan key poses on the beat sheet, then in-between with springs).

## Story beats for 15 to 25 seconds
| Time | Beat |
|---|---|
| 0.0 s | Frame 0 already shows the hook. Feeds autoplay muted, and early positive arousal predicts how widely a video is watched (Tong et al. 2020). No blank opening, no logo first. |
| 0 to 2 s | The hook lands: the problem in 5 to 7 words of large type, or the striking image. |
| 2 to 15 s | The mechanism or the build-up: a new visual payoff every 2 to 4 s, one idea per shot. |
| one moment | A deliberate stillness of 0.4 to 0.6 s before the key reveal. |
| last 2 to 3 s | The payoff and a sharp hold (no fade to black), the logo small. |
Write the beat sheet with times and locked copy before any code. Every paused frame should work as a cover (huashu-design): one subject, three moving elements at most, one path for the eye.

## Captions and words on screen (muted first)
- Every message is on screen as large type, not only in captions.
- 7 words or fewer per caption, on screen at least max(1.2 s, 0.3 s per word).
- A phrase holds still to be read before it moves; nothing moves across text being read.
- Keep text inside the platform's safe area (references/carousel.md).
- Deliver captions.srt for platforms that accept it (motion.mjs writes it from captions.json).

## Camera and cuts
- A locked camera, "like a drafting table", is often the most expensive look. If the camera moves, choose one or two operations (a slow push of 1.03 to 1.07 over a shot, a pan, a pull-back) and keep moves at least 2.5 s apart.
- Transitions that carry meaning: a match cut (the outgoing object lands on the incoming one's pixels), the object becomes the transition (it moves to camera and reveals the next scene behind it), a hard-edged colour flood. Avoid crossfades between unrelated shots and avoid blur-everything wipes.
- One signature move per film, repeated with variation, is better than ten different effects.

## Sound
Most feeds play muted, so the film must work without sound. If sound is used: licensed or code-made music only, effects on the beat, loudness about -14 LUFS for social.

## Checks
`python scripts/video_check.py <folder> --seconds 20` writes contact.png (one frame per second) and phone.png (360 px wide), and fails on: duration off by more than 2%, a still stretch of 3 s or more (a dead beat), black frames, a first caption later than 0.5 s, captions too short to read. Then `python scripts/attention.py <folder>/frame0.png` for the first frame. The critic reviews contact.png and phone.png, never the code.

## Banned in motion
Everything fading in the same way; bouncy easing; particle bursts; glows; typewriter or scramble text by default; spinning logos; a centred title on a gradient; "loading" shimmer as decoration; holds over 3 s with nothing new except the final hold; a loop seam that jumps (if it loops, the last frame equals the first).
