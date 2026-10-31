# Showing numbers

## Choose the encoding by how well people read it
Cleveland and McGill (1984) ranked how accurately people judge quantities: position on a common scale, then position on unaligned scales, then length, then angle and slope, then area, then volume, colour saturation and hue last. So:
| To show | Use | Avoid |
|---|---|---|
| comparison of a few values | bars (from zero), dots on a line | pies with more than 3 slices, 3D |
| change over time | a line; a slope chart for before and after | stacked areas with many layers |
| part of a whole | one stacked bar, a 10 x 10 grid of squares, a big number with its total | donuts with many slices |
| distribution | dots, a strip plot, a histogram | averages alone |
| one striking number | the number, huge, with its unit and its comparison | a chart around one number |
| scale (big counts) | a dot field where one dot = N units (the forecast direction) | icons of people repeated without a key |

## Edward Tufte's rules that matter on a phone ("The Visual Display of Quantitative Information", 1983)
- Maximise data ink: delete gridlines, borders, backgrounds and legends that do not carry data. Label lines directly at their ends.
- Small multiples: the same small chart repeated for each case beats one crowded chart.
- Show the comparison: a number alone means little; a number against last month, the target or the alternative means something.
- Chartjunk (decoration that carries no data) costs attention.

## The title says the finding
Not "Monthly reporting hours" but "Reporting takes 15 hours before anyone reads it". The chart is the proof of the title.

## Which number is big
The number that changes the viewer's mind gets the display size. A bigger number that matters less (a total, a headcount, a year) stays at body or label size. Name the key number in the brief, before the layout.

## Colour in charts
Grey for everything, the accent for the one series or bar that matters. If several series must be told apart, use a colour-blind-safe set (references/colour.md) and direct labels, never colour alone.
A state (before or after, pass or fail, us or them) keeps one colour and one label word on every page of a set, and the colour never appears without its word.

## Honesty
- Bars start at zero. Lines may not, but say so.
- Same scale across small multiples.
- Precise numbers only from real data, with the source in fine print. Sample or illustrative data is labelled "illustrative" on the page.
- Every number carries its period or as-of date in its source line ("Q3 2026", "as of 12 Oct 2026"). A number with no date is unfinished.
- A missing value is drawn as a labelled gap with its reason ("no data: not surveyed in 2024"), never as a zero, a dropped bar or a line smoothed across it.
- Show uncertainty when it exists: a range, a band, "about".
- Never invent percentages to fill a chart.

## In motion
A chart can draw itself from the same spring that moves the dot (one function of time drives both). Counters roll only while moving and settle sharply on the final value (`M.counter`). Hold the finished chart long enough to read: at least 2 s.
