import numpy as np
import pandas as pd

SCORE_FLOOR = 4.0
SCORE_BASE_TOP = 9.0
SCORE_CEILING = 10.0
PERFECT_THRESHOLD = 9.7
GAP_FULL_BONUS = 1.0


def to_ten_point(ranked: pd.DataFrame) -> pd.DataFrame:
    ranked = ranked.copy()
    s = ranked["strength"].to_numpy()

    if len(s) < 2 or s.max() == s.min():
        ranked["score_10"] = (SCORE_FLOOR + SCORE_BASE_TOP) / 2
        ranked["provisional"] = ranked["n_comparisons"] < 1
        return ranked

    pct = pd.Series(s).rank(pct=True).to_numpy()
    scaled = SCORE_FLOOR + (SCORE_BASE_TOP - SCORE_FLOOR) * pct

    order = np.argsort(-s)
    top_strength = s[order[0]]
    rest_mean = s[order[1:6]].mean() if len(s) > 5 else s[order[1:]].mean()
    gap = max(0.0, top_strength - rest_mean)

    bonus_room = SCORE_CEILING - SCORE_BASE_TOP
    for rank_pos, i in enumerate(order[:5]):
        film_gap = max(0.0, s[i] - rest_mean) if rank_pos > 0 else gap
        bonus = bonus_room * min(1.0, film_gap / GAP_FULL_BONUS)
        scaled[i] = min(SCORE_CEILING, scaled[i] + bonus)

    ranked["score_10"] = np.round(scaled, 1)
    ranked["provisional"] = ranked["n_comparisons"] < 1
    return ranked


def perfect_candidates(ranked: pd.DataFrame) -> pd.DataFrame:
    eligible = ranked[~ranked["provisional"]]
    return eligible[eligible["score_10"] >= PERFECT_THRESHOLD]