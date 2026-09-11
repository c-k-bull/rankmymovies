import pandas as pd
from ingest import load_export, add_signal_flags, add_priors
from enrich import enrich

films = add_priors(add_signal_flags(load_export("data/export"), "data/export"))
enriched, failures = enrich(films)

merged = films.merge(enriched, on="film_uri", how="left")
merged.to_csv("data/films_enriched.csv", index=False)

matched = merged["tmdb_id"].notna().sum()
print(f"\nmatch rate: {matched}/{len(merged)} ({100 * matched / len(merged):.1f}%)")
print("\nby tier:")
print(merged["match_tier"].value_counts())

if len(failures):
    print(f"\n{len(failures)} unmatched:")
    print(failures.to_string(index=False))