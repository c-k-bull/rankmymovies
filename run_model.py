import pandas as pd
from compare import load_log
from model import fit_strengths

films = pd.read_csv("data/films_pooled.csv")
pool = films[films["in_pool"]].copy()
log = load_log()

fit = fit_strengths(pool, log)
ranked = pool.merge(fit, on="film_uri").sort_values("strength", ascending=False)
ranked.to_csv("data/ranked.csv", index=False)

print(f"{len(log)} comparisons over {len(pool)} films")
print(f"films compared at least once: {(ranked['n_comparisons'] > 0).sum()}\n")

cols = ["name", "rating", "strength", "n_comparisons"]
print("TOP 20")
print(ranked.head(20)[cols].to_string(index=False))
print("\nBOTTOM 5")
print(ranked.tail(5)[cols].to_string(index=False))