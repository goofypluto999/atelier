# Words on the design

Design copy is read in under two seconds, at phone size, often by someone who did not choose to see it. Every word has to earn its place.

## Rules
- One claim per page or shot. The headline IS the claim; the rest is proof.
- Concrete beats abstract: a number with its unit, a named tool, a date, a real artefact. "Twelve steps between an order and its invoice", not "streamlining operational efficiency".
- Precise numbers only when real, with the source and its date or period in fine print. Never sharpen a number beyond its source.
- Plain verbs, active voice, short sentences, but varied rhythm: text where every sentence has the same length reads generated. `copy_lint.py` fails a coefficient of variation under 0.40 for texts of 6 sentences or more.
- A content word used three or more times across a set, or twice on one page, is a crutch: change it unless it is the subject's own term. `copy_lint.py` warns on repeated words; `--brand "Name"` and `--allow "word word"` keep the brand's name and the subject's own terms out of the count.
- No questions aimed at the viewer on covers ("Struggling with reporting?"); state the thing.
- The end carries something to keep (a rule, a check, a number), not a pitch.

## Word budget
A page gets about two seconds at phone size. Each page, and the one image of the quick scope, carries 45 words or fewer, every word counted, the source line too. Spend them like this:
- The hook: 8 words or fewer. references/type.md's headline budget gives about 16 to 20 characters a line at 92 to 120 px on a 920 px measure, so two lines hold 32 to 40 characters, about 6 to 8 words.
- The object's own labels: about 20 words (four to six labels of two to four words each).
- One line of proof: about 9 words, one 25 to 45 character line (references/type.md, social pages).
- The source: about 8 words.

One claim per page (above): the headline is the claim, the rest is proof, and the post text carries everything else (SKILL.md, quick path step 8). `render.mjs --audit` counts every page and warns above 45 with the number to cut. Cut before a critic sees the page: the hook to 8 words, then each label to its nouns, then every sentence but one. Evidence for the number: in the 30 Oct 2026 runs every page the art-director failed carried 71 to 92 words, and it named the count in its findings. The three strong calibration covers (evals/anchors/good-*.png) carry 19, 50 and 66 words, so the budget is stricter than two of them, on purpose: those two are a table and a form whose labels are the material.

## The five sins (each one embarrasses the brand; any one drops the piece)
| Sin | What it is | Test | Before, after |
|---|---|---|---|
| cringe | a claim about ourselves the evidence does not carry: announced feelings, hype, drama formatting, emoji, trend formats | would the author say it aloud to a sharp client? | "So proud of this game-changing launch 🚀" / "Version 2 ships today. It does one thing faster: exports." |
| preachy | telling the viewer how to think or work; universal claims; a lesson stated after the story already made it | is every general statement earned by our own story or a source on the page? | "You need to stop doing reports by hand." / "Our reports now assemble themselves at 06:00." |
| salesy | the piece exists to get a meeting: calls to action, "we help", promises of results, scarcity, gated value | delete the last line: did the viewer lose anything? | "Book a free audit today!" / (cut; the profile or the site does that job) |
| samey | the viewer has seen this piece from you before: same structure, same layout, same ending | cover the logo: could it be any of your last five? | (change the direction, then the structure; layout_memory.py checks covers) |
| slop | text that sounds generated: abstract nouns, "not just X, it's Y", triads by habit, summaries, words like crucial, pivotal, foster, landscape | read it aloud: where does it sound like a brochure? | "In today's evolving landscape, data is crucial." / "Fourteen sources, one sync, 0 rows rejected." |

Why the hard line: once people spot a sales or persuasion motive they discount the whole message (Friestad and Wright 1994), and controlling language ("you must", "you should") triggers resistance (reactance; meta-analysis Li and Shi 2026). People keep conclusions they reach themselves (Aronson 1999), so show the evidence and let the viewer conclude.

## AI tells in copy (from blader/humanizer, Wikipedia's "Signs of AI writing", and taste-skill)
Not-X-but-Y contrasts; one-line dramatic closers; rhetorical run-ups ("Here's the thing"); forced triads; stock words (delve, tapestry, testament, seamless, leverage, unlock, elevate, robust, game-changer, ever-evolving); inflated significance ("a pivotal moment"); summaries that repeat the page; the same sentence length every time; many em dashes. For long copy, run the humanizer skill (github.com/blader/humanizer, MIT) after drafting.

## Humour
At most one quiet moment: a deadpan verb, a precise detail placed flat after a big claim, an understatement, an object given a mood. Humour works when something is wrong and safe at once (McGraw and Warren 2010). No puns, memes, exclamation marks or emoji as punchlines.

## Check
`python scripts/copy_lint.py <file>` on post text, page HTML or captions.json. It catches the obvious patterns; the critique (references/critique.md) catches the rest, and must quote the line.
