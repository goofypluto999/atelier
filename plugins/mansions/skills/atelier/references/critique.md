# Critique: a reviewer that cannot be flattered

## Principles
- **Renders, not code.** The critic looks at the images (preview.png contact sheet, attention overlay, phone.png for video), never at the HTML, and never at the author's notes about what they meant or fixed.
- **Measured facts first.** Give the critic the script output (audit, attention, layout memory, video check) as facts. Huashu-design found that a model reviewing video alone found 3 of 14 dead stretches; given the measured freeze data it found all 14.
- **Independent eye.** Use a fresh subagent where possible. Self-review drifts toward approval; a stated rationale never lowers a finding's severity.
- **Quotes and locations.** Every finding names a page or a timestamp. A finding without a location does not count; a review without findings must still give "the strongest case to reject".
- **One item at a time.** Open each image right before judging it and start its entry with `seen:` quoting the largest words on it. In our first calibration run the critic judged all ten covers correctly but attached three verdicts to the wrong file numbers; the `seen:` line makes that visible.
- **Do not round up.** A first score of 9 or 10 is almost always wrong: score it again as someone who did not make it.

## The rubric (1 to 10 each)
| Dimension | Question | Cap |
|---|---|---|
| idea | Does the page carry a material only this subject could fill (the swap test)? | If another company could use these pages unchanged: idea 5 or less, and the total is capped at 6 |
| hook | At 360 px wide, is the hook what is read first, in under a second? | A cover that fails at 360 px: total capped at 6 |
| hierarchy | One subject and one path for the eye per page; one accent under 5% | |
| craft | Alignment, spacing, type sizes and weights, nothing clipped or overlapping | Any clipping or overlap: craft 4 or less |
| brand | Tokens, fonts, behaviour; no AI-look tells | A banned tell present: brand 5 or less |
| distinct | Does it look different from the last 8 pieces (layout memory, the recent covers sheet)? | |
| motion (video) | Frame 0 readable; something new every 2 to 4 s; captions readable; one signature move; a clean hold | A dead beat over 3 s: motion 5 or less |
| copy | No sins (references/copy.md); every number sourced | Any sin: copy 3 or less, and the piece is not delivered until fixed |
Total = the mean of the scores, after caps, to one decimal; never round it up. PASS needs a total of 7.5 or more, no cap applied and no FAIL-level flaw. Under 6 after three rounds: say so and offer a simpler format.

## Precision checks (every review)
Blind judges who preferred Atelier's pages still found these slips. Check each one on every page; each is a craft or copy finding with a location.
- **Count what is drawn.** Every drawn quantity matches its label: a bracket marked "100 users" must span 100 marks, not 90.
- **Only what the post says.** No headline, quote or claim on a page that the post text does not carry, even when it is in the sources.
- **No repeated state.** A page that shows the same state as an earlier page is cut or merged.
- **No false finish.** The close must not assert a done state that the post leaves open (a tick on a conditional, an owner signed off when the post says nobody is yet).
- **Labels at phone width.** Every label stays legible with the page shown 360 px wide; condensed caps labels fail first.
- **The right number is big.** The number that carries the claim is the largest number on the page. A bigger number that matters less is a hierarchy finding (references/dataviz.md).
- **Dates and gaps.** Every number has its period or as-of date in its source line. A missing value is a labelled gap with its reason, never a zero or a dropped bar.
- **The two-word read.** Before the detailed review, look at the contact sheet (page 1 for a single image) for about 2 seconds and write what it reads as in two words. If the words name neither the dealt direction nor the material idea, charge hierarchy.

## Output shape
```
reads as: <two words, after a 2-second look>
scores: idea n, hook n, hierarchy n, craft n, brand n, distinct n[, motion n], copy n  total n (capped: yes/no, why)
3 worst problems:
1. page 3 / 0:07: <what is wrong> -> <concrete fix>
2. ...
3. ...
keep: <the one thing that works and must survive the fixes>
strongest case to reject: <one sentence>
```

## Constructive, not destructive: how to critique so the notes get used
Critique that hurts gets dismissed; critique that is vague gets ignored. Rules for every critic in this skill:
- **Meaning first.** Start with what works and what it does for the viewer (adapted from Liz Lerman's Critical Response Process, which puts statements of meaning before opinions). It tells the maker what to protect.
- **Hard on the work, never the maker.** Describe the page, not the person ("the headline wraps to three lines", never "you rushed this").
- **Name the mechanism.** Every note names something measurable or quotable: a size, a contrast, an order, a spacing, a word, a claim. Banned in notes: pop, clean, modern, sleek, feels off, elevate, nice. compose.py refuses grade notes that lean on them.
- **Effect, then fix.** Each note has three parts: what you see (with its location), why it matters to the viewer (the principle), one concrete fix the maker could do in one revision. The fix is an option, not an order (Pixar's Braintrust: notes identify problems; the maker owns the solution).
- **Three, ranked.** At most three must-fix notes, ranked by how much they stop the one-line idea from landing. Everything else goes under "could improve", or is dropped. Piling on is a failure of judgement.
- **Rule or taste: say which.** A measured breach (contrast 3.1:1, a 3.4 s dead beat, a number with no source) is a rule. Everything else is judgement and is labelled as such.
- **Recreate or revise: say which.** If the idea, the angle or the material is the problem, polishing will not save it: recreate. If the execution is the problem: revise the three notes and keep the rest.
- **Grades carry evidence.** Every score has a "because" line quoting or locating its evidence. A grade without evidence is not a grade.

## The author's reply
For each finding: "Fixed: <what changed>" or "Disagree: <evidence>" (a measurement, a source, a brand rule). Never "great catch", never silence. At the round cap, every open finding gets a ruling: fixed, declined with reason, deferred.

## Calibrating the critic
Shipped set: evals/anchors (3 strong covers, 7 with one seeded flaw each: copy, hierarchy, tells, craft, legibility). `python scripts/calibrate.py prepare` shuffles them into `.atelier/calibration/<date>/`; give the critic only the NN files; save its JSON as verdicts.json; `python scripts/calibrate.py score <that file>`. Logged result on 29 Oct 2026, art-director on Sonnet: 7 of 7 flaws caught, 3 of 3 strong passed (evals/anchors/calibration-log.csv). The story-editor's run on evals/angles is logged the same way (5 of 5, 3 of 3). The verdict files of both runs were not kept: the log rows are the only record, so re-run the calibration before you rely on it.

A critic is only as good as its last test. Keep a small set of frozen examples with known answers in the project (for example `.atelier/anchors/`): three strong pieces and five with one seeded flaw each (a glow, a 20 px caption, an off-grid element, a salesy last line, a clipped headline). Before relying on a new critic prompt or model, run it blind on the shuffled set: it must fail every seeded flaw, naming it, and pass the strong ones. Re-run monthly; if the critic starts passing flaws, it has drifted, so tighten the prompt or use a stronger model. Never edit the answers to make a run pass.

## Contact sheets
`python scripts/contact_sheet.py <folder>` puts every page on one image: the critic sees rhythm, repetition and balance across the set, which page-by-page review misses. For video, `video_check.py` writes contact.png (one frame per second) and phone.png (phone width).
