# Drawn films: a world, a camera and a finish, in code

Use this when a film needs objects drawn and moved (a sheet, a list, a stamp, a board), a camera that pushes, glides and pulls across them, and a film finish. For type-led motion with a few moving parts, CSS keyframes or `window.seek(t)` with assets/lib/motion.js stay simpler (references/motion.md). Both render with the same script and pass the same checks.

The drawing code is vendored from huashu-art-motion by alchaincyf (MIT, commit 8a0d7d7; vendor/MANIFEST.md). The method below is rewritten from it for Atelier.

## The page
```html
<link rel="stylesheet" href="S/assets/tokens.css"> <link rel="stylesheet" href="palette.css">
<section class="page pg-1">
  <h1 data-role="hook">Words stay HTML, above the film.</h1>
</section>
<script src="S/vendor/huashu-art-motion/lib/util.js"></script>      <!-- U: clamp, lerp, U.rng(seed), eases -->
<script src="S/vendor/huashu-art-motion/lib/motion.js"></script>    <!-- MO: smooth, springs, slam, lagged, beats -->
<script src="S/vendor/huashu-art-motion/lib/camera.js"></script>    <!-- CAM: track, at, with, layer, toScreen -->
<script src="S/vendor/huashu-art-motion/lib/palettes.js"></script>  <!-- PAL: mix, alpha, contrast -->
<script src="S/vendor/huashu-art-motion/lib/finish.js"></script>    <!-- FINISH: soft, film, punch -->
<script src="S/assets/lib/art-motion.js"></script>
<script>
ART.film({ duration: 10, theme: "page", finish: "soft", draw(c, t, pal) { /* paint the frame for t */ } });
</script>
```
- `compose.py scaffold` writes the links as absolute paths; add the six script tags with the same absolute form (`S` is the skill folder).
- `theme: "page"` takes the colours from palette.css (`--ground`, `--text`, `--text-2`, `--accent`, `--accent-2`), so the dealt colour plan colours the film. A PAL name (`paper`, `ink`, `wood`, `bauhaus`, `snow`, `poster`, `navy`, `chalk`) replaces it only when the brief asks.
- Words are HTML with their `data-role`, so `render.mjs --audit` measures their size and contrast (it samples the drawn film under them) on the first frame, then checks every hard rule again every half second of the film (the length from `ART.film`) and at the poster time, and `attention.py` sees the hook. A word that must ride the camera is placed each frame from `CAM.toScreen(cam, x, y)`.
- A drawn object has no `data-role`, so `attention.py` reads it as decoration and fails the poster when the camera ends close on it. Mark it with an empty element that follows it: put `<div class="mark" data-role="object"></div>` (with `.mark { position: absolute; }`) in the section, and in `draw`, after the camera is set, place it on the object's box: `const [x0, y0] = CAM.toScreen(cam, left, top), [x1, y1] = CAM.toScreen(cam, right, bottom);` then set the mark's `left`, `top`, `width` and `height` from them. `render.mjs --audit --seconds N --poster T` records where the mark is at the poster time, and `attention.py` reads `poster.png` with it. tests/test_motion.py (`test_poster_object`) checks this: marked, the poster passes; unmarked, it fails as decoration.
- Render: `node S/scripts/motion.mjs visual.html --seconds 10 --sub 2 --poster 9`, then `render.mjs visual.html --audit --seconds 10 --poster 9`, `video_check.py <folder>` and the art-director. The page may load local files only; motion.mjs blocks any other request and fails.

## Shot list first
Above the table, three lines: the style in one sentence (one style for the whole film), the palette (palette.css, or 3 to 6 named colours), and the characters (none, or hands and backs only).
Columns: time, object (a noun you can point at), what it does (a verb), camera move, words on screen (7 or fewer, may be empty), how it is drawn.
1. The first 3 seconds are a small concrete scene, an object doing something about the topic, and frame 0 already carries the hook. The last shot lands on an object action (put away, stamped, pulled back to the whole), not on a centred quote card.
2. One object runs through the whole film, in one style, to the last frame.
3. A shot lasts 2 to 6 seconds; a few may reach 8.
4. Shots led by text are 30% or fewer, and never the first or the last.
5. Two shots in a row never share a composition: change the framing and the camera, not the style.
Red flags: in the object column, title, bullet, list, label, card, background, icon, empty frame, gradient; in the verb column, appear, show, display, fade in, one by one. A row without an object and a verb is not ready.

## Camera
Before each move, answer: where should the eye be, and can it read it at this framing (if so, hold)? Is the move a transition (slow) or an accent (fast, rare: a reveal, a key number)? What was the last move (after a push, pull out, glide or cut; never three pushes in a row)?

| Move | Use | Numbers | Code |
|---|---|---|---|
| Hold | reading; the picture moves by itself | as long as the read needs | no event |
| Push | lead the eye to the next detail | 0.6 to 1.5 s, 10 to 40% closer | `CAM.track(base, [{at, kind: "push", k: 0.2, x, y}], t)` (0.9 s) |
| Pull | back to the whole; the ending | 0.8 to 2 s, fast start, long tail | `kind: "pull"` (1.1 s) |
| Glide | from one item to the next | 0.5 to 0.9 s | `kind: "glide", x, y` (0.7 s) |
| Punch | accent: a reveal, a key number | 0.25 to 0.35 s, 18 to 32% closer, then hold | `kind: "punch"` (0.28 s) |
| Slam | a stamp or a number lands | 0.17 s, scale 1.55 to 0.94 to 1 | `kind: "slam"`, `MO.slam(t, at)` |
| Shake | with a slam, twice a film at most | 4 frames, 14 px | `kind: "shake"` |
| Cut | change framing with no move | 0 frames | `kind: "cut", x, y, z` |

Accents (punch, slam, pan) stay at a third of the shots or fewer; 8 or more pushes a minute is too many. The same move on every shot reads as a slideshow, slow or fast. Zoom with `CAM.zlerp` (even through scale) and draw vectors under the camera every frame, so a push stays sharp. `CAM.layer(c, cam, d, fn)` gives depth: layers with d under 1 move less.

## Motion and finish
- Springs and eases come from t only: `MO.spring(t - at, { duration: 0.5, bounce: 0.15 })`, `MO.smooth`, `MO.lagged(i, n, p)` for staggers, `MO.step(t, 12)` for a hand-drawn 12 fps feel. The rules in references/motion.md hold: no overshoot on type, exits faster than entrances, a stillness before the key reveal, a hold at the end, not a fade.
- Every random value comes from a seed: `const r = U.rng(7)` once, outside `draw`. No `Math.random`, no clock.
- `finish`: `soft` (light vignette, faint bloom, fine grain) suits most pieces; `film` is heavier and warmer; `punch` lifts contrast. The grain changes 24 times a second from a fixed seed, so the same t gives the same pixels.
- Cache what does not move (a paper texture, a static stack) in `init(pal)` on an offscreen canvas and draw only what moves.

## Six ways to fail
1. Slide deck: a fixed header, bullets fading in, the same move on every shot, a centred quote card at the end. One picture event per shot, varied moves, end on an object action.
2. Copying the demo: the specimen's or an example's composition carried into the film. Learn the grammar, redraw for the topic.
3. No concrete object: ideas shown only as words and icons. Every row names a thing and its action.
4. Dead or empty frame: a flat field that never changes while a small centre moves, or empty and black frames. The subject fills half the frame or more and is in every shot; something new every 2 to 4 seconds.
5. Drawing what exists as real material: put the real screen, document or photo full frame instead (references/imagery.md).
6. The instant AI look: blue to purple gradients, purple starfields, neon glow, a collage of styles, code-drawn mascots and robots. One style, one palette; people only as hands and backs.

## The alive test
A film is judged alive when, watched muted at phone size, every shot has a visible action by an object (drawn, moved, struck, stamped, stacked), the camera or the objects change the frame at least every 4 seconds, and no stretch looks like a still image with grain on it. A static or empty-feeling film fails, whatever its scores. `video_check.py` fails a stretch of 3 s or more with nothing new; the grain of a finish does not count as something new. The art-director applies the test to contact.png and phone.png.

## Not taken from the source
Its skill file and reference files (they tell the agent to edit the skill and to call GitHub on a timer), its Python scripts (unpinned inline dependencies), its renderer (it turns off browser web security), voice cloning, image fetching, its fonts, stroke data, showcase media and the author's likeness. The list with reasons: vendor/MANIFEST.md.
