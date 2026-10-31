# The worked run, step by step

One real run on 30 Oct 2026. The builder was Claude Opus 5.5. It followed the quick path in the main README on one topic, "what a Friday release checklist really needs", in an empty project folder with one file in it: `brand/fieldlark.css`, a made-up brand file written for the test (forest green, raspberry, and the faces Instrument Sans, Archivo and JetBrains Mono). Each piece had its own folder, and `palette.py`, `scaffold` and the checks ran from inside it. Every verdict came from a fresh art-director agent, given the full text of `atelier:art-director`, the slug, the render, the script output, the colour plan and the post text, and for pieces 2 and 3 the cover of piece 1. The times run from `new` to the last grade, critic time included.

Piece 1 ran on the code before the layout-memory fix. During piece 2 the run showed that `layout_memory.py`, run from a page's own folder, compared with no covers ("PASS against 0") and made an empty `.atelier` there. The fix (`layout_memory.py check` finds the project's covers from a page's folder) went in before piece 2's first critic, so pieces 2 and 3 were checked against piece 1's cover.

Two of three pieces passed. Piece 1 passed on its second attempt at 7.5. Piece 2 failed three attempts (6.0, 6.5 and 6.3), and compose.py sent it to a person. Piece 3, pinned to the warm register, passed on its third attempt at 7.5. Both passes sit on the bar: one point less on any criterion would fail them.

## Check it yourself

[evidence/](evidence) holds, for each piece, every critic verdict exactly as the critic wrote it (`verdict-N.md`), the render it judged (`page-N.png`), the audit (`audit-N.json`), the script output it was given (`checks-N.txt`), the post text it was given (`post-N.md`), the colour plan and the piece's `piece.json`. In `piece.json` the local folder paths are replaced by `<run>` and `<verdicts>`; nothing else is changed. The files have new names in this folder: piece.json's `<verdicts>\friday-brand-r1.md` is `friday-brand/verdict-1.md`, and so on (`<piece>-rN.md` is `<piece>/verdict-N.md`). The drawn film's piece.json names its verdicts in the other form the run used, `<run>\verdicts\<piece>-N.md`: `<run>\verdicts\friday-motion-1.md` is `friday-motion/verdict-1.md`. Each attempt's page is here as `visual-N.html`, with each piece's `palette.css` (as palette.py wrote it in the run) and the brand file the run used, [evidence/brand/fieldlark.css](evidence/brand/fieldlark.css). In those pages the absolute links to the skill and the run folder are replaced by `<skill>/` and `<run>/`. To render a page again, replace `<skill>` with your skill folder and `<run>` with this `evidence` folder, both as absolute paths with forward slashes, and render with `--out` to another folder: on 31 Oct 2026 all 8 image pages rendered this way passed `render.mjs --audit`. That replacement is the only change, but it changes the bytes, so a page's sha256 no longer matches the `html_sha256` a passing grade records (pieces 1 and 3); the sha256 of each original page is listed in [evidence/pages.txt](evidence/pages.txt). The sha256 of each verdict in `piece.json` (`stages.visual.grades[N].evidence.sha256`) matches the file next to it. [evidence/times.txt](evidence/times.txt) has the clock times.

## Piece 1, with the brand file (`friday-brand`), 9 min 31 s, PASS 7.5

1. **Topic.** `compose.py new friday-brand --topic "what a Friday release checklist really needs" --scope quick --medium image --brand brand/fieldlark.css`
2. **Atoms.** Five, each from a published source: roughly 70% of outages are due to changes in a live system, and the three answers to it (progressive rollouts, finding problems fast, rolling back safely), both from the Google SRE book, Introduction; a good checklist keeps to 5 to 9 items at a pause point (Gawande, The Checklist Manifesto, ch. 6); the WHO Surgical Safety Checklist, 19 items in three pauses of 7, 7 and 5; with it, deaths fell from 1.5% to 0.8% across 8 hospitals (Haynes et al., NEJM 2009). The same five atoms served all three pieces.
3. **Angle.** Dealt: "Put to another use", "Define the word", "No adjectives". The builder took the first: the WHO surgical checklist as a Friday release list in three pauses, none over nine checks.
4. **Genome, dealt:** direction `specimen-label`, register `play`, hook `anomaly`, close `question-answered`, harmony `complementary`, ground `paper`, layout `quote`. The brand file's faces were kept.
5. **Colour.** The brand's own colours: paper #f4f6f3, text #0f3d2e, accent #8e0940, text contrast 11.2:1.
6. **Build.** The headline "Nineteen surgical checks, seven at a time." over the three pauses, drawn as rows of nine slots with 7, 7 and 5 filled, against a raspberry wall after the ninth slot marked "One pause holds at most 9".
7. **Verdicts.**
   - Attempt 1, FAIL 7.2 (idea 7, hook 8, hierarchy 7, craft 6, colour 8, distinct 7). The wall and its 9 were the smallest marks, the counts sat at ragged x, and the empty slots were 2 px dashes.
   - `next` then printed "Start from attempt 1, the best so far (7.2)", that verdict's five fixes and its keep line. The builder applied those fixes and nothing else.
   - Attempt 2, PASS 7.5 (8, 8, 8, 7, 7, 7). Still charged: the empty slots measure 2.3:1 on the paper, the Gawande source sits under the Friday line, and the bar is not centred under the 9.
8. **Deliver.** `compose.py deliver friday-brand` wrote the memory and the cover.

## Piece 2, same topic, no brand file (`friday-plain`), 13 min 43 s, FAIL

9. **Angle.** Dealt: "The cost of not", "Failure first", "A provocation". The builder took "The cost of not": roughly seven in ten outages start with a change, so a Friday list that does not stop before the change leaves most of the risk unchecked.
10. **Genome.** Direction `transit-map`, register `craft-pride`, hook `comparison`, close `rule`, type `geometric` (Outfit, Work Sans), ground `paper`, layout `table`.
11. **Colour.** With no brand file, palette.py made the piece its own palette: paper #dde2d6, text #272b1e, accent #1e6c38, text contrast 11.0:1.
12. **Verdicts.**
    - Attempt 1, FAIL 6.0, capped (idea 5, hook 7, hierarchy 6, craft 6, colour 8, distinct 6). Seven and three dots on two lines: "a plain 7-in-10 unit chart", which fails the swap test.
    - Attempt 2, FAIL 6.5 (6, 7, 6, 7, 7, 6), the best. A stop bar labelled "Friday list" before the seven stations. The critic still read a bead chart, and read the rows of marks with a numeral on the right as one family with piece 1.
    - Attempt 3, FAIL 6.3 (6, 7, 6, 6, 7, 6). Rebuilt as a line map with a bend, as attempt 2's fixes asked; the stop bar now read as where the line starts.
13. **Stop.** `next` printed "visual: ESCALATE. 3 attempts, best 6.5 (kept in ...attempts/visual-2)", and `deliver` refused.

## Piece 3, the warm register (`friday-warm`), 13 min 55 s, PASS 7.5

14. `compose.py deal friday-warm genome --pin register=warmth`. Angle, dealt "The ratio": fifteen deaths in every thousand operations became eight once the surgical list stopped three times, the pause a Friday list can borrow. The first deal gave `transit-map`, which the builder judged a poor fit for a death rate. The worksheet says to deal again when an axis fights the angle; the second deal gave `timetable`, hook `artefact`, close `callback`, type `handnote` (Nothing You Could Do, Work Sans) and layout `sequence`.
15. **Colour.** palette.py's own warm palette: paper #e1d7cf, text #32261d, accent #864446, text contrast 10.4:1. The accent sits 0.20 OKLab from the ink, and the paper 0.074 from the warm cream of cluster 1: palette.py keeps both apart since this round.
16. **Verdicts.**
    - Attempt 1, FAIL 6.7 (7, 7, 5, 7, 7, 7). Two runs of the same three stops, theatre above and Friday below in the accent, with the death rate under the Friday run, where it read as the Friday list's result.
    - Attempt 2, FAIL 6.8 (7, 7, 6, 6, 7, 8). The rate moved under the theatre run, as attempt 1 asked. This critic said it now split the comparison, and that the script "1" read as a slash.
    - Attempt 3, PASS 7.5 (8, 7, 7, 7, 8, 8). The rate in words at the top, the two runs stacked on shared columns, the Friday stops with their questions. Still charged: the script headline is the thinnest stroke on the page, and the right margin is 101 px against 80.
17. **Deliver.** `compose.py deliver friday-warm`.

## Piece 4, a drawn film (`friday-motion`), 30 and 31 Oct 2026, FAIL

After the first three pieces, huashu-art-motion's drawing files were folded into the video path (`ART.film`, [references/art-motion.md](../../plugins/mansions/skills/atelier/references/art-motion.md)), and this piece tested it on the same topic and the same five atoms, in a new empty folder with no brand file. The builder was Claude Opus 5.5. Each verdict came from a fresh agent on Sonnet (the Agent tool's general-purpose agent with `model: sonnet`), told to follow `atelier:art-director` as written and to apply an alive test on top of the rubric: watched muted at phone size, every shot has an object doing something, the frame changes at least every 4 seconds, and nothing looks like a still image; a film that fails it fails whatever its scores. The model, the agent of each call and the clock times are in [evidence/friday-motion/times.txt](evidence/friday-motion/times.txt).

18. **Angle.** `compose.py new friday-motion --scope quick --medium video`. Dealt: "Ask the sceptic", "One shape, never cut", "An old idea from another field". The builder took "One shape, never cut": one long Friday list splits into three short ones on camera, 19 checks read 7, 7 and 5 at a time, as the surgical checklist does.
19. **Genome.** The first deal gave `type-only` (no pictures, the words are the image), which fights a drawn film, so the builder dealt again. The second: direction `kitchen-rail`, register `craft-pride`, hook `contradiction`, close `image`, harmony `split`, arc `cooldown`, ground `dark`. palette.py's own palette: ground #1d2514, text #e5eadf, accent #f9948c, text contrast 12.9:1.
20. **Build.** One ticket of 19 checks hangs on a rail under the hook; a bracket in the accent marks the 9 one pause can hold; the ticket is cut after checks 7 and 14 and hangs as three tickets, 7 before the change, 7 at go-live, 5 before you leave, which are ticked off. 10 s, 1080 x 1350, 30 fps, `--sub 2`; each render took about 6 minutes on this PC. Every attempt passed the audit, video_check.py (no dead beat, no black frame, duration 10.00 s), attention.py (the hook leads) and cvd.py.
21. **Verdicts.** Every critic answered `alive: yes`.
    - Attempt 1, FAIL 6.0, capped by craft 4 (idea 7, hook 7, hierarchy 7, craft 4, colour 5, distinct 7). The labels smeared and clipped while the camera glided across them, a tone step crossed the long ticket, and the hook said "holds nine" over tickets of 7, 7 and 5.
    - Attempt 2, FAIL 7.0, the best (7, 8, 7, 6, 7, 7). One wide hold from the cut on, the new hook "Nineteen checks. Nine at most per pause.", a real check line on each ticket. Charged: titles about 28 px as drawn, an empty lower band, and 3 s at the end with no object action.
    - Attempt 3, FAIL 6.7 (7, 7, 7, 6, 7, 6). The whole 19-row ticket shown once, taller tickets, a stamp on each ticket after its last tick, "Friday release" in the sub line. Charged: the cut that carries the idea is the film's least readable frame, the stamps cover row 4 and its line strikes "7 of 7", and the ticket lines are placeholders.
22. **Stop.** `next` printed "visual: ESCALATE. 3 attempts, best 7.0", and the piece goes to a person.
23. **Time.** 48 min 4 s of work across a stop: 43 min 29 s on 30 Oct, from `new` to the end of attempt 3's checks, when the app closed before critic 3 was called; then 4 min 35 s on 31 Oct for critic 3 and the last grade. The log says so where it happened.

Evidence, in [evidence/friday-motion](evidence/friday-motion): the three verdicts exactly as the critics wrote them (`verdict-N.md`, sha256 below), the script output each critic was given (`checks-N.txt`, with the run folder written as `<run>`), the contact and phone sheets, first frame and poster of attempts 2 and 3 (`contact-N.png`, `phone-N.png`, `frame0-N.png`, `poster-N.png`), attempt 3's video (`video-3.mp4`), each attempt's page (`visual-N.html`), the post text, the colour plan and `piece.json`. Attempt 1's sheets were overwritten by attempt 2's render and are not kept; its page is, and the render is deterministic, so `motion.mjs` makes them again. The sha256 of each verdict in `piece.json` matches the file next to it:
- verdict-1.md 3c7c061c5684098c199dfefc39a324e192cc8858eb3eedbd01b36fbd5bfec6e8
- verdict-2.md e9223f93dc875a574f1c62c5bd72956312bfe7a25ac0e2d1bcb438d7d8c08a68
- verdict-3.md a899ed4f0eb9aa7ecb9afdc8412ed2a2b15f6eeb40df6e6cc62e50989321aa0d

## What this run shows

- **Passes.** 2 of 3 pieces reached the 7.5 bar, each with no point to spare.
- **The revise step.** After every FAIL, `next` named the best attempt and printed its verdict's numbered fixes and keep line. Piece 1 went from 7.2 to 7.5 on those fixes alone. Piece 2 did not climb: its idea was the problem, and each critic asked for a different drawing. Piece 3's first two critics asked for opposite moves of the same line.
- **The five new audit warnings** fired on no page a critic saw: each fault was fixed or never built. No verdict charged a line under 36 px, a repeated claim, a wrapped run, an accent drawn under 8 px or an empty cell. Two verdicts still asked for a larger line at 36 or 40 px (piece 1's source line, piece 2's stop label).
- **Caught by a script since this run.** Piece 1's empty slots at 2.3:1 against the paper (a mark that carries meaning, under 3:1) and piece 3's thin script strokes each cost a point in a verdict, and no script warned on them in the run. The audit gained both warnings after this run. Re-rendered from the evidence, piece 1's passing page warns `faint mark` (`8 x i.free 2.3:1`), and piece 3's attempts 2 and 3 warn `thin stroke` (about 1.8 and 1.6 px on a phone).
- **Distinct** scored 7 or 8 in 5 of 8 verdicts. Piece 2 scored 6 three times, twice for looking like piece 1 (rows of marks with a numeral on the right).
- **The drawn film** (piece 4) passed every script and every critic's alive test, and failed all three critics' scores (6.0, 7.0, 6.7). The fixes each critic asked for were applied and nothing else, and each new attempt drew a different charge, as piece 2's did.
