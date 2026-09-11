import shutil
import zipfile
from pathlib import Path

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile

import storage
from ingest import load_export, add_signal_flags, add_priors
from enrich import enrich
from pool import build_pool

app = FastAPI()


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