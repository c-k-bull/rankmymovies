import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from tmdb import match_film, get_details, extract_fields

CACHE_PATH = Path("data/tmdb_cache.csv")
CACHE_MAX_AGE = timedelta(days=180)


def load_cache() -> dict[int, dict]:
    if not CACHE_PATH.exists():
        return {}

    df = pd.read_csv(CACHE_PATH)
    cutoff = datetime.now() - CACHE_MAX_AGE
    fresh = df[pd.to_datetime(df["fetched_at"]) > cutoff]

    return {int(r["tmdb_id"]): dict(r) for _, r in fresh.iterrows()}


def save_cache(cache: dict[int, dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(list(cache.values())).to_csv(CACHE_PATH, index=False)


def enrich(films: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cache = load_cache()
    rows, failures = [], []

    for i, film in films.iterrows():
        year = int(film["year"]) if pd.notna(film["year"]) else None
        hit, tier = match_film(film["name"], year)
        time.sleep(0.05)

        if hit is None:
            failures.append({"name": film["name"], "year": year, "tier": tier})
            continue

        tmdb_id = hit["id"]
        if tmdb_id not in cache:
            fields = extract_fields(get_details(tmdb_id))
            fields["fetched_at"] = datetime.now().isoformat()
            cache[tmdb_id] = fields
            time.sleep(0.05)

        rows.append({"film_uri": film["film_uri"], "match_tier": tier, **cache[tmdb_id]})

        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(films)}")

    save_cache(cache)
    return pd.DataFrame(rows), pd.DataFrame(failures)