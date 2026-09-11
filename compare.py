import random
from datetime import datetime
from pathlib import Path

import pandas as pd

LOG_PATH = Path("data/comparisons.csv")
LOG_COLUMNS = ["film_a", "film_b", "winner", "timestamp"]
CANDIDATE_PAIRS = 200


def load_log() -> pd.DataFrame:
    if LOG_PATH.exists():
        return pd.read_csv(LOG_PATH)
    return pd.DataFrame(columns=LOG_COLUMNS)


def append_comparison(film_a: str, film_b: str, winner: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = pd.DataFrame([{
        "film_a": film_a,
        "film_b": film_b,
        "winner": winner,
        "timestamp": datetime.now().isoformat(),
    }])
    header = not LOG_PATH.exists()
    row.to_csv(LOG_PATH, mode="a", header=header, index=False)


def pair_score(a: pd.Series, b: pd.Series) -> float:
    uncertainty = (a["prior_sd"] + b["prior_sd"]) ** 0.5
    closeness = 1.0 / (1.0 + abs(a["prior_mean"] - b["prior_mean"]))
    relevance = 2.0 ** min(a["prior_mean"], b["prior_mean"])
    return uncertainty * closeness * relevance


def select_pair(pool: pd.DataFrame, seen: set[frozenset]) -> tuple[pd.Series, pd.Series] | None:
    uris = pool["film_uri"].tolist()
    best, best_score = None, -1.0

    for _ in range(CANDIDATE_PAIRS):
        a_uri, b_uri = random.sample(uris, 2)
        if frozenset((a_uri, b_uri)) in seen:
            continue

        a = pool[pool["film_uri"] == a_uri].iloc[0]
        b = pool[pool["film_uri"] == b_uri].iloc[0]
        score = pair_score(a, b)

        if score > best_score:
            best, best_score = (a, b), score

    return best