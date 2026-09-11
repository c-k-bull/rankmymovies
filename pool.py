import pandas as pd

POOL_FLOOR = 60
POOL_CEILING = 175
POOL_FRACTION = 0.4
UNRATED_CAP = 15
UNRATED_CEILING = 50
SEED = 7


def pool_size(n: int) -> int:
    return min(n, POOL_CEILING, max(POOL_FLOOR, int(POOL_FRACTION * n)))


def build_pool(films: pd.DataFrame) -> pd.DataFrame:
    eligible = films[films["tmdb_id"].notna()].copy()
    target = pool_size(len(eligible))

    forced = eligible["is_liked"] | eligible["is_favorite"]
    plain_unrated = eligible["rating"].isna() & ~forced

    picked = eligible[forced].copy()

    n_rated_available = (eligible["rating"].notna() & ~forced).sum()
    shortfall = target - len(picked) - n_rated_available
    unrated_slots = min(
        max(UNRATED_CAP, shortfall),
        UNRATED_CEILING,
        target - len(picked),
        int(plain_unrated.sum()),
    )

    if unrated_slots > 0:
        picked = pd.concat([
            picked,
            eligible[plain_unrated].sample(n=unrated_slots, random_state=SEED),
        ])

    remaining = target - len(picked)
    rest = eligible[
        ~eligible["film_uri"].isin(picked["film_uri"]) & eligible["rating"].notna()
    ]
    rest = rest.sort_values(["prior_mean", "rating"], ascending=False)
    picked = pd.concat([picked, rest.head(remaining)])

    films = films.copy()
    films["in_pool"] = films["film_uri"].isin(picked["film_uri"])
    return films