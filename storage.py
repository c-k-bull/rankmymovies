import uuid

import pandas as pd
from sqlalchemy import text

from db import engine

import json


def new_session() -> str:
    sid = uuid.uuid4().hex[:12]
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO sessions (session_id, state) VALUES (:sid, 'queued')"),
            {"sid": sid},
        )
    return sid


def exists(sid: str) -> bool:
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT 1 FROM sessions WHERE session_id = :sid"), {"sid": sid}
        ).first()
    return row is not None


def write_status(sid: str, state: str, done: int = 0, total: int = 0) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE sessions SET state = :state, done = :done, total = :total
                WHERE session_id = :sid
            """),
            {"sid": sid, "state": state, "done": done, "total": total},
        )


def read_status(sid: str) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT state, done, total FROM sessions WHERE session_id = :sid"),
            {"sid": sid},
        ).mappings().first()
    return dict(row) if row else {"state": "unknown", "done": 0, "total": 0}


def save_films(sid: str, films: pd.DataFrame) -> None:
    clean = films.astype(object).where(pd.notna(films), None)
    records = clean.to_dict(orient="records")
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM films WHERE session_id = :sid"), {"sid": sid})
        conn.execute(
            text("""
                INSERT INTO films (session_id, film_uri, data)
                VALUES (:sid, :uri, :data)
            """),
            [
                {"sid": sid, "uri": r["film_uri"], "data": json.dumps(r, default=str)}
                for r in records
            ],
        )


def load_films(sid: str) -> pd.DataFrame:
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT data FROM films WHERE session_id = :sid"), {"sid": sid}
        ).scalars().all()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def append_comparison(sid: str, film_a: str, film_b: str, winner: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO comparisons (session_id, film_a, film_b, winner)
                VALUES (:sid, :a, :b, :w)
            """),
            {"sid": sid, "a": film_a, "b": film_b, "w": winner},
        )


def load_log(sid: str) -> pd.DataFrame:
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT film_a, film_b, winner, created_at
                FROM comparisons WHERE session_id = :sid ORDER BY id
            """),
            {"sid": sid},
        ).mappings().all()
    if not rows:
        return pd.DataFrame(columns=["film_a", "film_b", "winner", "created_at"])
    return pd.DataFrame([dict(r) for r in rows])


def append_exclusion(sid: str, film_uri: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO exclusions (session_id, film_uri) VALUES (:sid, :uri)
                ON CONFLICT DO NOTHING
            """),
            {"sid": sid, "uri": film_uri},
        )


def load_exclusions(sid: str) -> set:
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT film_uri FROM exclusions WHERE session_id = :sid"),
            {"sid": sid},
        ).scalars().all()
    return set(rows)