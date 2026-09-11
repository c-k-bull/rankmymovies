import uuid
from pathlib import Path

import pandas as pd

SESSIONS_DIR = Path("sessions")


def new_session() -> str:
    sid = uuid.uuid4().hex[:12]
    (SESSIONS_DIR / sid).mkdir(parents=True, exist_ok=True)
    return sid


def session_path(sid: str, name: str) -> Path:
    return SESSIONS_DIR / sid / name


def exists(sid: str) -> bool:
    return (SESSIONS_DIR / sid).is_dir()


def write_status(sid: str, state: str, done: int = 0, total: int = 0) -> None:
    pd.DataFrame([{"state": state, "done": done, "total": total}]).to_csv(
        session_path(sid, "status.csv"), index=False
    )


def read_status(sid: str) -> dict:
    p = session_path(sid, "status.csv")
    if not p.exists():
        return {"state": "unknown", "done": 0, "total": 0}
    return pd.read_csv(p).iloc[0].to_dict()