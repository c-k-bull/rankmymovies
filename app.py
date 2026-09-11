import shutil
import zipfile
from pathlib import Path

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile

import storage
from ingest import load_export, add_signal_flags, add_priors
from enrich import enrich
from pool import build_pool
from fastapi import Body
from compare import select_pair

app = FastAPI()

POSTER_BASE = "https://image.tmdb.org/t/p/w500"


def load_session_films(sid: str) -> pd.DataFrame:
    path = storage.session_path(sid, "films.csv")
    if not path.exists():
        raise HTTPException(409, "session not ready")
    return pd.read_csv(path)


def load_session_log(sid: str) -> pd.DataFrame:
    path = storage.session_path(sid, "comparisons.csv")
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=["film_a", "film_b", "winner", "timestamp"])


def film_payload(row: pd.Series) -> dict:
    poster = row.get("poster_path")
    return {
        "film_uri": row["film_uri"],
        "name": row["name"],
        "year": int(row["year"]) if pd.notna(row["year"]) else None,
        "poster": f"{POSTER_BASE}{poster}" if pd.notna(poster) else None,
    }


@app.get("/pair/{sid}")
async def get_pair(sid: str):
    films = load_session_films(sid)
    log = load_session_log(sid)

    excluded = set()
    ex_path = storage.session_path(sid, "exclusions.csv")
    if ex_path.exists():
        excluded = set(pd.read_csv(ex_path)["film_uri"])

    pool = films[films["in_pool"] & ~films["film_uri"].isin(excluded)]
    seen = {frozenset((r["film_a"], r["film_b"])) for _, r in log.iterrows()}

    pair = select_pair(pool, seen)
    if pair is None:
        return {"done": True, "count": len(log)}

    a, b = pair
    return {
        "done": False,
        "count": len(log),
        "a": film_payload(a),
        "b": film_payload(b),
    }


@app.post("/comparison/{sid}")
async def post_comparison(sid: str, film_a: str = Body(...),
                          film_b: str = Body(...), winner: str = Body(...)):
    if winner not in (film_a, film_b):
        raise HTTPException(400, "winner must be one of the two films")

    path = storage.session_path(sid, "comparisons.csv")
    row = pd.DataFrame([{
        "film_a": film_a, "film_b": film_b, "winner": winner,
        "timestamp": pd.Timestamp.now().isoformat(),
    }])
    row.to_csv(path, mode="a", header=not path.exists(), index=False)

    return {"count": len(load_session_log(sid))}


@app.post("/exclude/{sid}")
async def post_exclude(sid: str, film_uri: str = Body(..., embed=True)):
    path = storage.session_path(sid, "exclusions.csv")
    row = pd.DataFrame([{
        "film_uri": film_uri,
        "timestamp": pd.Timestamp.now().isoformat(),
    }])
    row.to_csv(path, mode="a", header=not path.exists(), index=False)
    return {"excluded": film_uri}

def process_export(sid: str) -> None:
    try:
        export_dir = storage.session_path(sid, "export")
        films = add_priors(add_signal_flags(load_export(export_dir), export_dir))

        storage.write_status(sid, "enriching", 0, len(films))
        enriched, failures = enrich(films)

        merged = films.merge(enriched, on="film_uri", how="left")
        merged = build_pool(merged)
        merged.to_csv(storage.session_path(sid, "films.csv"), index=False)

        storage.write_status(sid, "ready", len(merged), len(merged))
    except Exception as e:
        storage.write_status(sid, f"error: {e}")


@app.post("/upload")
async def upload(file: UploadFile, background: BackgroundTasks):
    sid = storage.new_session()
    zip_path = storage.session_path(sid, "export.zip")

    with open(zip_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    export_dir = storage.session_path(sid, "export")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(export_dir)

    profile = export_dir / "profile.csv"
    favorites = ""
    if profile.exists():
        favorites = pd.read_csv(profile)["Favorite Films"].iloc[0]
        profile.unlink()
    (export_dir / "favorites.txt").write_text(str(favorites))

    zip_path.unlink()
    storage.write_status(sid, "queued")
    background.add_task(process_export, sid)

    return {"session_id": sid}


@app.get("/status/{sid}")
async def status(sid: str):
    if not storage.exists(sid):
        raise HTTPException(404, "unknown session")
    return storage.read_status(sid)