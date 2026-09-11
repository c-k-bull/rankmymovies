import pandas as pd
from pool import build_pool

films = pd.read_csv("data/films_enriched.csv")
films = build_pool(films)
films.to_csv("data/films_pooled.csv", index=False)

pool = films[films["in_pool"]]
print(f"pool: {len(pool)} of {films['tmdb_id'].notna().sum()} eligible\n")
print("composition:")
print("  rated:", pool["rating"].notna().sum())
print("  liked:", pool["is_liked"].sum())
print("  favorites:", pool["is_favorite"].sum())
print("  unrated:", pool["rating"].isna().sum())
print("\nlowest-rated film in pool:", pool["rating"].min())
print("\nsample of pool:")
print(pool.nlargest(10, "prior_mean")[["name", "rating", "is_liked"]].to_string(index=False))