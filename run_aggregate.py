import pandas as pd
from aggregate import aggregate, subcategory_confidence

ranked = pd.read_csv("data/ranked.csv")

SUBCATEGORIES = [
    ("directors", "DIRECTORS", False, 2),
    ("genres", "GENRES", True, 4),
    ("cast", "ACTORS", False, 3),
]

for field, label, idf, minf in SUBCATEGORIES:
    agg = aggregate(ranked, field, use_idf=idf, min_films=minf)
    conf = subcategory_confidence(ranked, agg, field)

    if conf["unlocked"]:
        status = "unlocked"
    elif conf["more_needed"] is None:
        status = "not enough data"
    elif conf["more_needed"] >= 400:
        status = "400+ more comparisons"
    else:
        status = f"{conf['more_needed']} more comparisons"

    leaders = " & ".join(conf["leaders"]) if conf["leaders"] else "—"
    print(f"\n{label}  [{status}]  separation={conf['separation']:.2f}")
    print(f"  top: {leaders}")