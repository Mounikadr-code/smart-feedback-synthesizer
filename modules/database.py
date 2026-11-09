"""SQLite storage layer.

This file is the project's "memory": every feedback row that is ever uploaded
is saved here and stays here until the user clears the database.
"""
import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "feedback.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_text TEXT NOT NULL,
    source TEXT NOT NULL,
    feedback_date TEXT NOT NULL,
    sentiment TEXT,
    polarity REAL,
    category TEXT,
    topic TEXT,
    hindsight_synced INTEGER DEFAULT 0,
    text_hash TEXT NOT NULL UNIQUE,
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS upload_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    rows_received INTEGER,
    rows_added INTEGER,
    rows_skipped INTEGER,
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create the tables if they do not exist yet."""
    with closing(_connect()) as conn:
        conn.executescript(SCHEMA)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(feedback)")]
        if "hindsight_synced" not in cols:      # upgrade databases created by older versions
            conn.execute("ALTER TABLE feedback ADD COLUMN hindsight_synced INTEGER DEFAULT 0")
        conn.commit()


def make_hash(text, source, date):
    """Fingerprint of a feedback row. Same text + source + date = duplicate."""
    key = f"{str(text).strip().lower()}|{str(source).strip().lower()}|{pd.Timestamp(date).strftime('%Y-%m-%d')}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def insert_feedback(df, filename="Manual entry", rows_received=None):
    """Save analysed feedback. Rows already stored are silently skipped.

    Returns a dict with how many rows were added and how many were skipped.
    """
    init_db()
    rows = [
        (
            r.feedback_text,
            r.source,
            pd.Timestamp(r.feedback_date).strftime("%Y-%m-%d"),
            r.sentiment,
            float(r.polarity),
            r.category,
            r.topic,
            make_hash(r.feedback_text, r.source, r.feedback_date),
        )
        for r in df.itertuples(index=False)
    ]
    received = rows_received if rows_received is not None else len(rows)
    with closing(_connect()) as conn:
        before = conn.total_changes
        conn.executemany(
            "INSERT OR IGNORE INTO feedback "
            "(feedback_text, source, feedback_date, sentiment, polarity, category, topic, text_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        added = conn.total_changes - before
        conn.execute(
            "INSERT INTO upload_log (filename, rows_received, rows_added, rows_skipped) VALUES (?, ?, ?, ?)",
            (filename, int(received), int(added), int(received - added)),
        )
        conn.commit()
    return {"added": added, "already_stored": len(rows) - added}


def load_feedback():
    """Return all stored feedback as a DataFrame (empty if nothing stored)."""
    init_db()
    with closing(_connect()) as conn:
        df = pd.read_sql_query("SELECT * FROM feedback ORDER BY feedback_date, id", conn)
    if not df.empty:
        df["feedback_date"] = pd.to_datetime(df["feedback_date"])
    return df


def update_analysis(df):
    """Overwrite sentiment/category/topic for stored rows (used by 're-run analysis')."""
    rows = [
        (r.sentiment, float(r.polarity), r.category, r.topic, int(r.id))
        for r in df.itertuples(index=False)
    ]
    with closing(_connect()) as conn:
        conn.executemany(
            "UPDATE feedback SET sentiment=?, polarity=?, category=?, topic=? WHERE id=?", rows
        )
        conn.commit()


def get_upload_log():
    init_db()
    with closing(_connect()) as conn:
        return pd.read_sql_query(
            "SELECT filename AS File, rows_received AS Received, rows_added AS Added, "
            "rows_skipped AS Skipped, uploaded_at AS 'Uploaded at (UTC)' "
            "FROM upload_log ORDER BY id DESC",
            conn,
        )


def clear_database():
    """Delete everything. Only called when the user explicitly asks."""
    init_db()
    with closing(_connect()) as conn:
        conn.execute("DELETE FROM feedback")
        conn.execute("DELETE FROM upload_log")
        conn.commit()


def get_unsynced(limit=50):
    """Feedback rows not yet sent to Hindsight (problems and requests first)."""
    init_db()
    with closing(_connect()) as conn:
        return pd.read_sql_query(
            "SELECT * FROM feedback WHERE hindsight_synced = 0 "
            "ORDER BY CASE WHEN category IN ('Positive Feedback','General Feedback') THEN 1 ELSE 0 END, "
            "feedback_date DESC LIMIT ?", conn, params=(int(limit),))


def mark_synced(ids):
    if not ids:
        return
    with closing(_connect()) as conn:
        conn.executemany("UPDATE feedback SET hindsight_synced = 1 WHERE id = ?", [(int(i),) for i in ids])
        conn.commit()


def count_unsynced():
    init_db()
    with closing(_connect()) as conn:
        return conn.execute("SELECT COUNT(*) FROM feedback WHERE hindsight_synced = 0").fetchone()[0]
