import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")
BASE = "https://api.themoviedb.org/3"

# prompts TMDB API with movie name and year, retrieves movie metadata
def search_movie(name: str, year: int | None = None) -> list[dict]:
    params = {"api_key": API_KEY, "query": name}
    if year is not None:
        params["primary_release_year"] = year

    resp = requests.get(f"{BASE}/search/movie", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()["results"]

def best_exact(results: list[dict], name: str, year: int | None,
               max_year_gap: int = 3) -> dict | None:
    exact = [r for r in results if r["title"].lower() == name.lower()]

    if year is not None:
        exact = [
            r for r in exact
            if r.get("release_date", "")[:4].isdigit()
            and abs(int(r["release_date"][:4]) - year) <= max_year_gap
        ]

    if not exact:
        return None
    return max(exact, key=lambda r: r.get("popularity", 0))


def match_film(name: str, year: int | None) -> tuple[dict | None, str]:
    if year is not None:
        results = search_movie(name, year)
        if results:
            return max(results, key=lambda r: r.get("popularity", 0)), "exact_year"

        for offset in (-1, 1):
            hit = best_exact(search_movie(name, year + offset), name, year)
            if hit:
                return hit, f"year{offset:+d}"

    hit = best_exact(search_movie(name, None), name, year)
    if hit:
        return hit, "no_year"

    return None, "unmatched"

def get_details(tmdb_id: int) -> dict:
    params = {"api_key": API_KEY, "append_to_response": "credits"}
    resp = requests.get(f"{BASE}/movie/{tmdb_id}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def extract_fields(detail: dict) -> dict:
    credits = detail.get("credits", {})

    directors = [
        c["name"] for c in credits.get("crew", [])
        if c.get("job") == "Director"
    ]
    cast = [c["name"] for c in credits.get("cast", [])[:5]]
    genres = [g["name"] for g in detail.get("genres", [])]

    return {
        "tmdb_id": detail["id"],
        "tmdb_title": detail["title"],
        "release_date": detail.get("release_date"),
        "runtime": detail.get("runtime"),
        "poster_path": detail.get("poster_path"),
        "genres": "|".join(genres),
        "directors": "|".join(directors),
        "cast": "|".join(cast),
    }

if __name__ == "__main__":
    for name, year in [
        ("Lady Bird", 2017),
        ("Squid Game", 2021),
        ("Parasite", 2019),
        ("Ocean's Eight", 2018),
        ("tick, tick... BOOM!", 2021),
    ]:
        hit, tier = match_film(name, year)
        if hit:
            print(f"{tier:12} {hit['id']:>8} {hit['title']} ({hit['release_date'][:4]})")
        else:
            print(f"{tier:12} {'—':>8} {name} ({year})")