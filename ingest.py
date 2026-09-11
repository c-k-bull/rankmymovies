from pathlib import Path
import pandas as pd

# GLOBAL VARIABLES - UNIT IS STANDARD DEVIATION
LIKE_BOOST = 0.5
FAVORITE_BOOST = 1.0
PRIOR_SD_RATED = 0.5
PRIOR_SD_UNRATED = 1.5

# loads letterboxd csv and combines watched + rated into one list
def load_export(export_dir: str) -> pd.DataFrame:
    d = Path(export_dir)

    watched = pd.read_csv(d / "watched.csv")
    films = watched.rename(columns={
        "Letterboxd URI": "film_uri",
        "Name": "name",
        "Year": "year",
        "Date": "date_added",
    })

    ratings = pd.read_csv(d / "ratings.csv").rename(columns={
        "Letterboxd URI": "film_uri",
        "Rating": "rating",
    })

    films = films.merge(ratings[["film_uri", "rating"]], on="film_uri", how="left")

    return films

# flags for films that lie in special categories (liked, favorite)
def add_signal_flags(films: pd.DataFrame, export_dir: str) -> pd.DataFrame:
    d = Path(export_dir)

    likes = pd.read_csv(d / "likes" / "films.csv")
    films["is_liked"] = films["film_uri"].isin(likes["Letterboxd URI"])

    fav_path = d / "favorites.txt"
    fav_field = fav_path.read_text().strip() if fav_path.exists() else ""
    fav_uris = [u.strip() for u in fav_field.split(",") if u.strip()]
    films["is_favorite"] = films["film_uri"].isin(fav_uris)

    return films

# adds bonuses to liked films and favorite films, a rated film has the most certain score
# and a completely blank film (only watched) has the least certain score
def add_priors(films: pd.DataFrame) -> pd.DataFrame:
    mu = films["rating"].mean()
    sd = films["rating"].std()

    if sd == 0 or pd.isna(sd):
        sd = 1.0

    rated = films["rating"].notna()

    films["prior_mean"] = 0.0
    films.loc[films["is_liked"], "prior_mean"] = LIKE_BOOST
    films.loc[films["is_favorite"], "prior_mean"] = FAVORITE_BOOST
    films.loc[rated, "prior_mean"] = (films["rating"] - mu) / sd

    films["prior_sd"] = PRIOR_SD_UNRATED
    films.loc[rated, "prior_sd"] = PRIOR_SD_RATED

    return films

if __name__ == "__main__":
    films = load_export("data/export")
    films = add_signal_flags(films, "data/export")
    films = add_priors(films)

    print(films.shape)
    print("rated:", films["rating"].notna().sum())
    print("liked & unrated:", (films["is_liked"] & films["rating"].isna()).sum())
    print()
    print(films.groupby("prior_sd")["prior_mean"].describe()[["count", "mean", "min", "max"]])

    films.to_csv("data/films.csv", index=False)
    print("wrote data/films.csv")