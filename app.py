import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
from fastapi import BackgroundTasks, Body, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import storage
from db import init as db_init
from ingest import load_export, add_signal_flags, add_priors
from enrich import enrich
from pool import build_pool
from compare import select_pair
from model import fit_strengths
from aggregate import aggregate, subcategory_confidence
from score import to_ten_point, perfect_candidates

app = FastAPI()

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=os.getenv("ALLOWED_ORIGIN_REGEX"),
    allow_methods=["*"],
    allow_headers=["*"],
)

POSTER_BASE = "https://image.tmdb.org/t/p/w500"

SUBCATEGORIES = [
    ("directors", False, 2),
    ("genres", True, 4),
    ("cast", False, 3),
]


@app.on_event("startup")
def startup():
    db_init()


def process_export(sid: str, export_dir: str) -> None:
    try:
        films = add_priors(add_signal_flags(load_export(export_dir), export_dir))

        storage.write_status(sid, "enriching", 0, len(films))
        enriched, failures = enrich(
            films,
            on_progress=lambda done, total: storage.write_status(
                sid, "enriching", done, total
            ),
        )

        merged = films.merge(enriched, on="film_uri", how="left")
        merged = build_pool(merged)
        storage.save_films(sid, merged)

        storage.write_status(sid, "ready", len(merged), len(merged))
    except Exception as e:
        import traceback
        traceback.print_exc()
        storage.write_status(sid, f"error: {type(e).__name__}: {e}"[:500])
    finally:
        shutil.rmtree(export_dir, ignore_errors=True)


def get_films(sid: str) -> pd.DataFrame:
    films = storage.load_films(sid)
    if films.empty:
        raise HTTPException(409, "session not ready")
    return films


def film_payload(row: pd.Series) -> dict:
    poster = row.get("poster_path")
    return {
        "film_uri": row["film_uri"],
        "name": row["name"],
        "year": int(row["year"]) if pd.notna(row["year"]) else None,
        "poster": f"{POSTER_BASE}{poster}" if pd.notna(poster) else None,
    }


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/upload")
async def upload(file: UploadFile, background: BackgroundTasks):
    sid = storage.new_session()

    work = Path(tempfile.mkdtemp(prefix=f"rmm-{sid}-"))
    zip_path = work / "export.zip"
    export_dir = work / "export"

    with open(zip_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(export_dir)
    except zipfile.BadZipFile:
        shutil.rmtree(work, ignore_errors=True)
        storage.write_status(sid, "error: not a zip file")
        raise HTTPException(400, "that file isn't a zip")

    profile = export_dir / "profile.csv"
    favorites = ""
    if profile.exists():
        favorites = pd.read_csv(profile)["Favorite Films"].iloc[0]
        profile.unlink()
    (export_dir / "favorites.txt").write_text(str(favorites))

    zip_path.unlink()
    storage.write_status(sid, "queued")
    background.add_task(process_export, sid, str(export_dir))

    return {"session_id": sid}


@app.get("/status/{sid}")
async def status(sid: str):
    if not storage.exists(sid):
        raise HTTPException(404, "unknown session")
    return storage.read_status(sid)


@app.get("/pair/{sid}")
async def get_pair(sid: str):
    films = get_films(sid)
    log = storage.load_log(sid)
    excluded = storage.load_exclusions(sid)

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

    storage.append_comparison(sid, film_a, film_b, winner)
    return {"count": len(storage.load_log(sid))}


@app.post("/exclude/{sid}")
async def post_exclude(sid: str, film_uri: str = Body(..., embed=True)):
    storage.append_exclusion(sid, film_uri)
    return {"excluded": film_uri}


@app.get("/results/{sid}")
async def get_results(sid: str):
    films = get_films(sid)
    log = storage.load_log(sid)

    if len(log) < 10:
        return {"ready": False, "count": len(log), "needed": 10 - len(log)}

    excluded = storage.load_exclusions(sid)
    pool = films[films["in_pool"] & ~films["film_uri"].isin(excluded)].copy()

    fit = fit_strengths(pool, log)
    ranked = pool.merge(fit, on="film_uri").sort_values("strength", ascending=False)
    ranked = to_ten_point(ranked)

    top = [
        {**film_payload(r), "score": float(r["score_10"]),
         "provisional": bool(r["provisional"]),
         "n_comparisons": int(r["n_comparisons"])}
        for _, r in ranked.head(25).iterrows()
    ]

    subcats = {}
    for field, idf, minf in SUBCATEGORIES:
        agg = aggregate(ranked, field, use_idf=idf, min_films=minf)
        conf = subcategory_confidence(ranked, agg, field)

        entries = []
        if conf["unlocked"]:
            for _, r in agg.head(8).iterrows():
                members = ranked[
                    ranked[field].fillna("").str.contains(re.escape(r["key"]))
                ]
                entries.append({
                    "name": r["key"],
                    "score": float(r["score"]),
                    "n_films": int(r["n_films"]),
                    "films": [
                        {**film_payload(m), "score": float(m["score_10"]),
                         "n_comparisons": int(m["n_comparisons"])}
                        for _, m in members.head(10).iterrows()
                    ],
                })

        subcats[field] = {
            "unlocked": conf["unlocked"],
            "leaders": conf["leaders"],
            "more_needed": conf["more_needed"],
            "entries": entries,
        }

    cands = perfect_candidates(ranked)

    return {
        "ready": True,
        "count": len(log),
        "top_films": top,
        "subcategories": subcats,
        "perfect_candidates": [film_payload(r) for _, r in cands.iterrows()],
    }