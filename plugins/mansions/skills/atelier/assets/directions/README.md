# Direction specimens

Each file is the cover of one art direction, built on ../tokens.css with sample content. There are 19: 17 art directions plus two formats (slide-16x9.html at 1920 x 1080, story-9x16.html at 1080 x 1920). directions.png shows them all; `node ../../scripts/specimens.mjs` re-renders them (with your brand file loaded in tokens.css or after it). The library and how a direction is dealt: ../../references/directions.md.

## Use one
1. Let the composer start the page: `python <skill>/scripts/compose.py scaffold <slug> --out visual.html` writes a composition start for the dealt direction into your project, not a copy of its specimen: the grid, the dealt type and palette.css, each page set up for its dealt layout word, with absolute links, the logo slot filled from your brand file's `--logo` (or removed), and the next command. The art-director judges a page's distinctness against the specimen of its direction, so read the specimen here for the grammar's rules, leave its frame, and do not reuse its stock parts unchanged (data/directions.json names each frame and its stock parts; references/directions.md lists them).
2. Copying a file by hand also works (the page then keeps the specimen's frame, which scores low on distinct), but its links are relative (`../tokens.css`, `../lib/`) and break in your project: point them at the skill's absolute path. `render.mjs --audit` fails on a broken link, a missing image or a fallback font, so a missed path does not pass silently.
3. Replace the sample content with real material. Keep the data-role attributes on the hook, number or object, accent, logo and fine print.
4. Fill the empty logo slot with your own logo. The Mansions logo is a trademark of The Mansions Agency and is not licensed to you.
5. Add pages as more `<section class="page">` blocks in the same grammar.
6. Render and check: `node <skill>/scripts/render.mjs visual.html --audit` (it writes the PNGs too), then `python <skill>/scripts/attention.py <folder>`.

## Motion
departure-board.motion.html shows the motion pattern: frame 0 already shows the hook, then `window.seek(t)` paints every frame from time alone with the springs in ../lib/motion.js. Render: `node <skill>/scripts/motion.mjs departure-board.motion.html --seconds 8 --sub 2 --poster 7`.
