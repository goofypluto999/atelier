# Why it works: the evidence, graded

Strength: **strong** (replicated or meta-analysed), **medium** (one solid study or a review), **weak** (small, unreplicated, or a failed replication: treat as a hypothesis). Checked October 2026. Real proof for your audience comes from your own results: log the direction, format and hook of every piece next to its numbers and compare after 10 to 20 pieces.

## Attention and perception
| Finding | Source | Strength | Rule it supports |
|---|---|---|---|
| Bottom-up attention is pulled by local contrast in intensity, colour and orientation before meaning is processed. | Itti, Koch and Niebur 1998, IEEE PAMI | strong (a classic, widely replicated model) | attention.py; one pop-out per page |
| Text and faces attract fixations regardless of their low-level contrast. | Cerf, Frady and Koch 2009, Journal of Vision | medium | the audit's "hook is the biggest type" check; attention.py underrates text |
| Viewers fixate the centre of a frame first. | Judd, Ehinger, Durand and Torralba 2009, ICCV | strong | the hook near the optical centre or top-left of centre; attention.py's mild centre bias |
| An item that differs from its context is remembered. | von Restorff 1933; Hunt 1995, PB&R, https://doi.org/10.3758/BF03214414 | strong | one accent per page |
| Easy-to-process visuals and text are liked and trusted more. | Reber, Schwarz and Winkielman 2004, PSPR, https://doi.org/10.1207/s15327957pspr0804_3 | strong | floors, contrast, one claim per page; it pulls against novelty, hence MAYA |
| The best-liked designs are both typical and novel. | Hekkert, Snelders and van Wieringen 2003, BJP, https://doi.org/10.1348/000712603762842147 | medium | one novel element per piece |
| Quantities are judged most accurately by position, then length, then angle, area and colour. | Cleveland and McGill 1984, JASA | strong | references/dataviz.md |
| The peak and the end dominate memory of an experience. | Kahneman et al. 1993; meta-analysis Alaybek et al. 2022, https://doi.org/10.1016/j.obhdp.2022.104149 | strong (the plain average predicts nearly as well) | the last page and the last shot carry the takeaway |

## Engagement and persuasion
| Finding | Source | Strength | Rule it supports |
|---|---|---|---|
| Early positive arousal in a video's opening seconds forecast aggregate views; viewers' own ratings did not. | Tong et al. 2020, PNAS, https://doi.org/10.1073/pnas.1905178117 | medium (n=36) | frame 0 carries the hook; open on interest or delight, not threat |
| Content that is about the viewer and good for the sharer's standing predicted sharing. | Scholz et al. 2017, PNAS, https://doi.org/10.1073/pnas.1615259114 | medium | the brief's audience and delta |
| High-arousal emotions (awe, anger, anxiety) raise sharing; positive content is shared more. | Berger and Milkman 2012, JMR, https://doi.org/10.1509/jmr.10.0353 | medium | aim for awe and curiosity; anger and anxiety cost trust |
| Curiosity needs a specific, visible gap that looks closable. | Loewenstein 1994, Psych Bulletin, https://doi.org/10.1037/0033-2909.116.1.75 | medium (theory) | the brief's tension |
| Recognised persuasion tactics are discounted. | Friestad and Wright 1994, JCR, https://doi.org/10.1086/209380 | medium (model) | no selling on the page |
| Controlling language raises reactance and lowers persuasion. | Li and Shi 2026, HCR, https://doi.org/10.1093/hcr/hqaf016 (meta-analysis) | strong, small effects | no "you must" |
| Absorbed readers adopt story-consistent beliefs. | Green and Brock 2000, JPSP, https://doi.org/10.1037/0022-3514.79.5.701 | strong | scenes, timelines, object biographies |
| Humour lands when a violation is also benign. | McGraw and Warren 2010, Psych Science, https://doi.org/10.1177/0956797610376073 | medium | one quiet smile, never a punchline |
| Precise figures make a speaker seem more confident. | Jerez-Fernandez, Angulo and Oppenheimer 2014, Psych Science, https://doi.org/10.1177/0956797613504301 | medium | real, precise numbers |
| Faces in images raise likes and comments on Instagram. | Bakhshi, Shamma and Gilbert 2014, CHI, https://doi.org/10.1145/2556288.2557403 | medium, one platform | test faces on covers |
| Concrete wording is judged more likely true. | Hansen and Wänke 2010 | weak: failed a preregistered replication (Henderson et al. 2019) | not used as a reason; be concrete for clarity |

## AI reviewers
LLM judges favour the first option shown, longer answers and their own writing (Zheng et al. 2023, https://arxiv.org/abs/2306.05685). Pairwise comparison beat direct scoring in some studies (Liu et al. 2024) and flipped more under distractors in others (Tripathi et al. 2025). Hence: show options in both orders, require quotes and locations, calibrate the critic against known answers (references/critique.md).

## Not used, and why
Brain-response predictors such as Meta's TRIBE v2 are sometimes suggested as "neuro" scores for content. As of October 2026 its licence is non-commercial (CC BY-NC 4.0), and no published test links its predictions to social performance. The studies above are the evidence such tools try to imitate.
