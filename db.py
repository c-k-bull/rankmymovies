import os

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("DATABASE_URL", "postgresql+psycopg://localhost/rankmymovies")
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(url, pool_pre_ping=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    done INT DEFAULT 0,
    total INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS films (
    session_id TEXT NOT NULL,
    film_uri TEXT NOT NULL,
    data JSONB NOT NULL,
    PRIMARY KEY (session_id, film_uri)
);

CREATE TABLE IF NOT EXISTS comparisons (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    film_a TEXT NOT NULL,
    film_b TEXT NOT NULL,
    winner TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS comparisons_session ON comparisons (session_id);

CREATE TABLE IF NOT EXISTS exclusions (
    session_id TEXT NOT NULL,
    film_uri TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (session_id, film_uri)
);

CREATE TABLE IF NOT EXISTS tmdb_cache (
    tmdb_id BIGINT PRIMARY KEY,
    data JSONB NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT now()
);
"""


def init() -> None:
    with engine.begin() as conn:
        for stmt in SCHEMA.strip().split(";\n\n"):
            if stmt.strip():
                conn.execute(text(stmt))