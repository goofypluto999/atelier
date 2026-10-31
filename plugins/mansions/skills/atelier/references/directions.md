# Art directions: a library to deal from

A direction is a grammar: a borrowed real-world form (a ledger, a board, a card, a map) plus rules for type, ground, accent and motion. The brand stays constant (tokens, fonts, logo); the grammar changes, so a feed of pieces reads as one family and never as one template.

Specimens with a built cover are in assets/directions/ (see directions.png). `node S/scripts/specimens.mjs` renders page 1 of each with the bundled tokens.css and overwrites specimens/*.png and directions.png in the skill folder (in a plugin install, in the plugin cache); it has no brand option. The others ("build" in the table) are described well enough to build; when you build one, add a specimen.

## Static and carousel directions
| id | Borrowed form and grammar | Ground | Best for | Specimen |
|---|---|---|---|---|
| task-card | Aircraft maintenance task card: ruled boxes, TASK / APPLIES TO fields, a WARNING block, numbered steps, a sign-off box with a stamp. Plain-language rules are its native voice. | paper | rules, procedures, checklists, what we changed | yes |
| ledger | Accounting ledger: double rule at the top, ruled rows, a margin rule, right-aligned tabular numbers, a pencil tick on the total. | paper | costs, time, budgets, anything that adds up | yes |
| departure-board | Split-flap board: tiles with a horizontal split, statuses, one tile in the accent. Flaps flip in motion. | dark | queues, statuses, schedules, automations | yes (+ motion) |
| receipt | Till roll on a dark ground: monospaced items, dashed separators, a total in the accent, a torn edge. | paper on dark | per-run costs, itemised comparisons | yes |
| specimen-label | Museum mount: one object drawn large, a catalogue label with dry facts. | paper, dark mount | an object with a story, legacy tools, artefacts | yes |
| field-notebook | Grid paper, timestamps in the margin, tape, one circled number. | paper | logs, tests, observations, scenes | yes |
| editorial-poster | Swiss poster: one enormous number or word, a strict grid, a single rule, small text in columns. | full accent field | one striking number, a manifesto line | yes |
| transit-map | Metro diagram: sources as stations, flows as coloured lines, one interchange. | paper | data flows, integrations, journeys | yes |
| diff | Changelog or code diff: removed lines struck through, added lines in the accent, a plain-English commit message. | dark | changes, versions, before and after | yes |
| index-card | Library catalogue card: typed heading with part of speech, a definition, "see also", a stamp, a punched hole. | card on accent field | definitions, glossaries, reframes | yes |
| forecast | Weather console: a dot field (each dot = N units), fronts and pressure lines, a legend bar. | dark | simulations, scenarios, predictions (no invented percentages) | yes |
| blueprint | Drafting sheet: dimension lines, a title block, one lit part, construction lines. | dark or blue-black | architectures, designs not yet built | yes |
| kitchen-rail | Order tickets clipped to a rail, each a job, stamped when done. | dark steel | queues, handoffs, throughput | yes |
| field-guide | Natural-history plate: specimens drawn in a row, labelled with Latin-style names, a key. | paper | taxonomies, types of customer or failure | build |
| manual-page | Appliance manual: exploded diagram, numbered callouts, "do not" icons. | paper | how something works inside | yes |
| timetable | Rail timetable grid: times down, stations across, one highlighted run. | paper | schedules, before and after timings | yes |
| newspaper | Broadsheet front page: masthead, columns, one headline, a photo caption. | newsprint | announcements, a story told as news (use sparingly) | build |
| type-only | No pictures: the words are the image. Scale, weight and width do all the work (variable fonts help). | any | manifesto lines, quotes, one idea | yes |
| colour-chapters | Each page is a full field of one brand colour; the change of field marks the chapter. Neighbouring fields differ in lightness, not only hue. | brand fields | multi-part stories | yes |
| page-is-the-object | The page IS the artefact: a real postmortem, runbook, receipt, contract clause, laid out as itself. | as the object | anything with a real document behind it | build |
| product-performs | The real product UI, cropped and staged, doing one real action per page. | product's own | product posts (real screenshots only) | build |

Formats with specimens: slide-16x9.html (1920 x 1080) and story-9x16.html (1080 x 1920, inside the UI safe zones).

The newspaper direction sits in a generated-design cluster (references/tells.md); use it only when the subject is news.

## Motion-native directions (paraphrased from the community motion briefs credited in CREDITS.md, in this skill's folder)
| id | Concept | Best for |
|---|---|---|
| single-shape | One container never cuts: it morphs from button to loader to card to chart to toast; a cursor drives each change; the last frame equals the first so it loops. | product flows |
| three-inks | One line promoted three times: pencil on paper, then a blueprint wire, then light on black. It never leaves the screen. | the life of an idea, design to build |
| words-as-architecture | Each word or line becomes a beam; the final claim stands on what earlier words built. | manifestos, principles |
| cost-machine | Engraved number wheels, belts and gates; every movement is one cost operation. | pricing, cost design |
| night-shift | One take: a clock runs through the night while rooms go dark and results appear. | automation, "while you sleep" without the cliché words |
| the-dot | One accent dot traces a curve, becomes the cursor, becomes the end card. | a single metric's story |
| job-ticket | A ticket types its rows, gets stamped, and its stub tears off. | requests, approvals |

## How a direction is dealt
You do not deal by hand. `python S/scripts/compose.py deal <slug> genome` (S is this skill's folder) deals ONE direction as part of the genome:
1. Only directions whose `media` in data/directions.json include the piece's medium are in the pool.
2. Each is weighted by 1 / (1 + its uses in the last 20 pieces) to the power alpha, read from `.atelier/history.jsonl`; a direction already used for the same topic is excluded.
3. The whole genome must differ from each of the last 10 pieces on a minimum number of axes, and empty cells of register x operator family x ground are preferred, so grounds keep changing.
4. Write: "On these pages, [material] becomes [device], drawn as [the object's own form], not as [the stock part it replaces]." If the device carries no information about the subject, deal again (the next deal excludes this one).

Start the page with `python S/scripts/compose.py scaffold <slug> --out visual.html`. It writes the page with absolute links, so nothing breaks when the file sits in your project. For an image or a carousel it is a composition start on the grid in the dealt type and colours, each page set up for its dealt layout word, never the specimen's page: the art-director judges distinct against the specimen, so read the specimen for the grammar's rules, leave its frame, and keep its stock parts (below) off the page unless the object changes them (data/directions.json names each specimen's layout, frame and stock parts). Quick scope deals only directions that have a specimen, so there is always a picture of the grammar to read. In full and design scope a direction without a specimen (`"specimen": false` in data/directions.json: the four marked "build" above and six of the motion-native ones) gives a plain start, and scaffold says so.

## Stock parts: build the device out of the object
A direction lends rules (a ledger adds up, a map connects, a manual takes a thing apart), not drawings. Build its device out of the topic's own object, with the object's count, shape, labels and order: the WHO checklist's three pauses are three pauses, not three rhombi. The parts below are the specimens' stock parts. None of them may appear unchanged on a page: turn each into a form the object has, or leave it out. In the 30 Oct 2026 runs of the README example, with the specimen's frame gone, the critics still read parts like these as the specimen (the poster's numeral and hairline, the map's rings, the manual's rhombi). 04-genome.md and 07-visual.md list them for the dealt direction (data/directions.json "stock").

| id | Stock parts that must not appear unchanged |
|---|---|
| task-card | a ruled card with TASK, APPLIES TO and SINCE boxes; a WARNING bar with a thick rule on its left; three numbered steps; a SIGNED and STATUS row with a tilted GATED stamp |
| ledger | a double rule over WHEN, ITEM and HOURS column heads; rows of day, item and hours with the hours right-aligned; a total row with its number in the accent |
| departure-board | a black board of split-flap letter tiles in SERVICE, ROUTE and STATUS columns; one WAIT status in accent tiles |
| receipt | a till roll on the right that runs off the top edge; a RUN number over token, retry and cache lines, the retries struck through; a TOTAL with its amount in an accent box; a zigzag torn foot |
| specimen-label | a sheet of paper on a dark mount, held by a pin; a catalogue label under it with a rule on its left and a catalogue number |
| field-notebook | a squared grid over the whole page; times in a margin column left of a vertical rule; one number in a drawn circle; tape strips on two corners |
| editorial-poster | one huge numeral filling the top half of a colour field; a full-width hairline rule under the numeral; a bold claim and a small note side by side in two columns under the rule |
| transit-map | hollow ring stations; lines that bend into one large interchange ring and branch out to the right; station names set beside their rings |
| diff | a dark code block with a file and version line; a removed line struck through after a minus; added lines after a plus on an accent band; a Why: note under the block |
| index-card | one tilted ruled card on a colour field; a headword in capitals followed by n.; a See also: line; a stamp box at the top right and a punched hole at the foot |
| forecast | a field of dots in two colours split by one curve; triangle markers along the curve; a legend line in monospace at the foot |
| blueprint | three labelled boxes joined by arrows; a dimension line with its measure; a SHEET, SCALE and STATUS title block at the bottom right |
| kitchen-rail | a full-width rail; four equal numbered tickets hanging from it; one tilted ticket in the accent marked WAIT; DONE stamps on the other tickets |
| timetable | a ruled table with a step column and two time columns; one time cell filled in the accent |
| manual-page | three stacked rhombi, an exploded stack of plates; dashed leaders to numbered circles in the accent; a do-not box with a barred circle at the foot |
| type-only | three or four lines of mixed weight and width filling the page; the last lines in the accent |
| colour-chapters | three horizontal bands of colour, one per chapter; a heading at the top left of each band with a small note under it |

## Building a new direction
A direction earns its place when it borrows a real form with its own rules (a ledger has ruled columns and totals for a reason) and when that form carries information about the subject. Build one cover specimen with the brand tokens, run `render.mjs --audit` and `attention.py` on it, add it to this table and to directions.png, and list its stock parts in data/directions.json "stock" and in the table above. Reject it if the swap test fails: if a competitor's piece could use the same page unchanged, it is decoration.

## Rules that hold in every direction
- Brand tokens and fonts only (references/brand.md). The direction changes grammar, never identity.
- The hook is the biggest type on the cover; the one accent sits on the one thing to remember.
- Build at the direction's intensity: the specimen sets the level of finish. A maximal direction built timidly fails, and so does a minimal one with stray ornament.
- Real material: the receipt's lines are real costs, the board's rows are real jobs, the diff's lines are the real change. Sample content is labelled.
