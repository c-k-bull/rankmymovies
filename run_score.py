import pandas as pd
from score import to_ten_point, perfect_candidates

ranked = pd.read_csv("data/ranked.csv")
ranked = to_ten_point(ranked)
ranked.to_csv("data/ranked.csv", index=False)

print("TOP 15")
print(ranked.head(15)[["name", "rating", "score_10", "n_comparisons"]].to_string(index=False))

cands = perfect_candidates(ranked)
print()
if len(cands) == 0:
    print("no perfect 10s — yet")
else:
    print(f"{len(cands)} perfect-10 candidate(s):")
    for _, f in cands.iterrows():
        print(f"  {f['name']} — is this a perfect ten?")