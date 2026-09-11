import numpy as np
import pandas as pd

SHRINKAGE_K = 5.0
MIN_FILMS = 2
SEPARATION_TARGET = 1.5
MAX_MORE_NEEDED = 400
MAX_LEADERS = 4


def subcategory_confidence(ranked: pd.DataFrame, agg: pd.DataFrame,
                           field: str) -> dict:
    empty = {"unlocked": False, "separation": 0.0,
             "more_needed": None, "leaders": []}
    if len(agg) < 2:
        return {**empty, "leaders": agg["key"].tolist()}

    exploded = explode_field(ranked, field)
    sd = ranked.set_index("film_uri")["posterior_sd"]

    def entry_uncertainty(key: str) -> float:
        films = exploded[exploded["key"] == key]
        sds = sd.reindex(films["film_uri"]).to_numpy()
        return np.sqrt(np.nansum(sds ** 2)) / max(len(sds), 1)

    top_uncertainty = entry_uncertainty(agg.iloc[0]["key"])
    top_score = agg.iloc[0]["score"]

    i = 1
    while i < len(agg) and (top_score - agg.iloc[i]["score"]) < top_uncertainty:
        i += 1

    leaders = agg.iloc[:i]["key"].tolist()

    if len(leaders) > MAX_LEADERS:
        return {"unlocked": False, "separation": 0.0,
                "more_needed": MAX_MORE_NEEDED, "leaders": []}

    if i >= len(agg):
        return {"unlocked": False, "separation": 0.0,
                "more_needed": MAX_MORE_NEEDED, "leaders": leaders}

    gap = top_score - agg.iloc[i]["score"]
    separation = gap / top_uncertainty if top_uncertainty > 0 else 0.0

    if separation >= SEPARATION_TARGET:
        return {"unlocked": True, "separation": separation,
                "more_needed": 0, "leaders": leaders}

    current = ranked["n_comparisons"].sum() / 2
    factor = (SEPARATION_TARGET / separation) ** 2 if separation > 0 else 4.0
    more = int(np.ceil(current * (factor - 1)))

    return {"unlocked": False, "separation": separation,
            "more_needed": min(more, MAX_MORE_NEEDED), "leaders": leaders}

def explode_field(ranked: pd.DataFrame, field: str) -> pd.DataFrame:
    df = ranked[["film_uri", "name", "strength", "n_comparisons", field]].copy()
    df = df[df[field].notna()]
    df[field] = df[field].str.split("|")
    df["share"] = 1.0 / df[field].str.len()
    return df.explode(field).rename(columns={field: "key"})


def aggregate(ranked: pd.DataFrame, field: str,
              k: float = SHRINKAGE_K, min_films: int = MIN_FILMS,
              use_idf: bool = False) -> pd.DataFrame:
    exploded = explode_field(ranked, field)
    global_mean = ranked["strength"].mean()

    counts = exploded.groupby("key")["share"].sum()
    exploded["weight"] = exploded["share"] * (1.0 + np.sqrt(exploded["n_comparisons"]))

    rows = []
    for key, grp in exploded.groupby("key"):
        n = len(grp)
        if n < min_films:
            continue

        w = grp["weight"].to_numpy()
        raw = np.average(grp["strength"].to_numpy(), weights=w)
        evidence = w.sum()
        score = (evidence * raw + k * global_mean) / (evidence + k)

        if use_idf:
            idf = 1.0 / counts[key]
            score = global_mean + (score - global_mean) * idf * counts.mean()

        top = grp.nlargest(1, "strength").iloc[0]
        rows.append({
            "key": key,
            "n_films": n,
            "raw_mean": raw,
            "score": score,
            "evidence": evidence,
            "top_film": top["name"],
        })

    return pd.DataFrame(rows).sort_values("score", ascending=False)