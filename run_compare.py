import pandas as pd

from compare import load_log, append_comparison, select_pair

N_COMPARISONS = 40

films = pd.read_csv("data/films_pooled.csv")
pool = films[films["in_pool"]].copy()

log = load_log()
seen = {frozenset((r["film_a"], r["film_b"])) for _, r in log.iterrows()}

print(f"pool: {len(pool)} films | already answered: {len(log)}")
print("\nWhich would you rather experience for the first time again?")
print("type 1 or 2, s to skip, q to quit\n")

answered = 0
while answered < N_COMPARISONS:
    pair = select_pair(pool, seen)
    if pair is None:
        print("no pairs left")
        break

    a, b = pair
    print(f"[{len(log) + answered + 1}]")
    print(f"  1. {a['name']} ({int(a['year'])})")
    print(f"  2. {b['name']} ({int(b['year'])})")

    choice = input("> ").strip().lower()

    if choice == "q":
        break

    seen.add(frozenset((a["film_uri"], b["film_uri"])))

    if choice == "s":
        print()
        continue

    if choice not in ("1", "2"):
        print("  ? type 1, 2, s, or q\n")
        continue

    winner = a["film_uri"] if choice == "1" else b["film_uri"]
    append_comparison(a["film_uri"], b["film_uri"], winner)
    answered += 1
    print()

print(f"\nanswered {answered} this session")