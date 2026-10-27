"""P2c: precision and recall of the default threshold on 17 INVENTED headline pairs (8 the same story, 9 not).

This measures what the rule does to pairs I wrote myself. It is NOT evidence about real news and the pairs are too few
to tune on; the numbers are pinned so a change to the threshold, the shingles or the entity step shows up as a visible
change. The defaults under-merge short rewordings (recall below 1) and cannot tell a
one-word reversal ("high" against "low") from a rewording, so they merge that pair: lexical similarity has no sense of
meaning. Both errors distort a story count and a corroboration count."""

from __future__ import annotations

from fno.ingestion.news.cluster.cluster import cluster_articles
from tests.ingestion.news.cluster.helpers import AS_OF, art, at

SAME_STORY = [
    ("Nifty ends higher as IT stocks rally", "Nifty ends higher as IT stocks rally - Mint"),
    ("RBI keeps repo rate unchanged at 6.5 per cent", "RBI keeps repo rate unchanged at 6.5 per cent, stance neutral"),
    (
        "Reliance Industries Q2 profit rises 9 percent",
        "Reliance Industries Q2 profit rises 9 percent to Rs 19,000 crore",
    ),
    ("Sensex jumps 400 points on banking gains", "Sensex jumps 400 points on strong banking gains"),
    ("TCS wins large deal from European insurer", "TCS bags large deal from European insurer"),
    ("Rupee falls to record low against dollar", "Rupee falls to a record low against the dollar"),
    ("Oil prices surge after Opec cuts output", "Oil prices surge as Opec cuts output"),
    ("Infosys raises revenue guidance for FY27", "Infosys raises FY27 revenue guidance"),
]
DIFFERENT_STORIES = [
    ("Nifty ends higher as IT stocks rally", "Nifty options: traders eye 25000 call writing"),
    ("RBI keeps repo rate unchanged at 6.5 per cent", "RBI governor says inflation risks remain elevated"),
    ("Reliance Industries Q2 profit rises 9 percent", "Reliance Retail plans 500 new stores this year"),
    ("Sensex jumps 400 points on banking gains", "Sensex falls 300 points as metals drag"),
    ("TCS wins large deal from European insurer", "TCS announces buyback of shares worth Rs 17,000 crore"),
    ("Rupee falls to record low against dollar", "Rupee gains against dollar on foreign inflows"),
    ("Oil prices surge after Opec cuts output", "Oil marketing companies cut fuel prices in Delhi"),
    ("Infosys raises revenue guidance for FY27", "Infosys appoints new chief financial officer"),
    (
        "Nifty closes at record high",
        "Nifty closes at record low",
    ),  # a known false positive: one opposite word (judge 52)
]


def merged(first: str, second: str) -> bool:
    return len(cluster_articles([art("a", first, at(5)), art("b", second, at(4))], AS_OF).clusters) == 1


def test_the_default_threshold_on_invented_pairs_has_precision_5_of_6_and_recall_5_of_8():
    true_positive = sum(merged(*pair) for pair in SAME_STORY)
    false_positive = sum(merged(*pair) for pair in DIFFERENT_STORIES)
    assert (true_positive, len(SAME_STORY) - true_positive, false_positive) == (5, 3, 1)
