import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.models import Track, Design, CardSet

DB_PATH = Path(__file__).parent.parent / "data" / "bingo.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with _connect() as conn:
        conn.executescript(schema)


# ── Playlists ──────────────────────────────────────────────────────────────────

def save_playlist(playlist_id: str, name: str, tracks: list[Track]) -> None:
    tracks_json = json.dumps([t.to_dict() for t in tracks], ensure_ascii=False)
    with _connect() as conn:
        conn.execute(
            """INSERT INTO playlists (id, name, fetched_at, tracks_json)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name,
                 fetched_at=excluded.fetched_at,
                 tracks_json=excluded.tracks_json""",
            (playlist_id, name, datetime.now().isoformat(), tracks_json),
        )


def load_playlist(playlist_id: str) -> Optional[tuple[str, list[Track]]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT name, tracks_json FROM playlists WHERE id = ?", (playlist_id,)
        ).fetchone()
    if not row:
        return None
    tracks = [Track.from_dict(d) for d in json.loads(row["tracks_json"])]
    return row["name"], tracks


def list_playlists() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, fetched_at, tracks_json FROM playlists ORDER BY fetched_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        tracks = json.loads(r["tracks_json"])
        result.append({
            "id": r["id"],
            "name": r["name"],
            "fetched_at": r["fetched_at"],
            "track_count": len(tracks),
        })
    return result


def delete_playlist(playlist_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))


# ── Designs ───────────────────────────────────────────────────────────────────

def save_design(name: str, image_path: str, grid_x: int, grid_y: int, grid_w: int, grid_h: int) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO designs (name, image_path, grid_x, grid_y, grid_w, grid_h, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, image_path, grid_x, grid_y, grid_w, grid_h, datetime.now().isoformat()),
        )
        return cur.lastrowid


def load_design(design_id: int) -> Optional[Design]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM designs WHERE id = ?", (design_id,)).fetchone()
    if not row:
        return None
    return Design(
        id=row["id"], name=row["name"], image_path=row["image_path"],
        grid_x=row["grid_x"], grid_y=row["grid_y"],
        grid_w=row["grid_w"], grid_h=row["grid_h"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def list_designs() -> list[Design]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM designs ORDER BY created_at DESC").fetchall()
    return [
        Design(
            id=r["id"], name=r["name"], image_path=r["image_path"],
            grid_x=r["grid_x"], grid_y=r["grid_y"],
            grid_w=r["grid_w"], grid_h=r["grid_h"],
            created_at=datetime.fromisoformat(r["created_at"]),
        )
        for r in rows
    ]


def delete_design(design_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM designs WHERE id = ?", (design_id,))


# ── Card Sets ─────────────────────────────────────────────────────────────────

def save_card_set(
    name: str,
    playlist_id: str,
    design_id: int,
    num_cards: int,
    show_cover_art: bool,
    seed: int,
    cards: list[list[Track]],
    stats: dict,
    pdf_path: Optional[str] = None,
) -> int:
    cards_json = json.dumps(
        [[t.to_dict() for t in card] for card in cards],
        ensure_ascii=False,
    )
    stats_json = json.dumps(stats, ensure_ascii=False)
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO card_sets
               (name, playlist_id, design_id, num_cards, show_cover_art, seed,
                cards_json, stats_json, pdf_path, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name, playlist_id, design_id, num_cards, int(show_cover_art), seed,
                cards_json, stats_json, pdf_path, datetime.now().isoformat(),
            ),
        )
        return cur.lastrowid


def load_card_set(card_set_id: int) -> Optional[tuple[CardSet, list[list[Track]]]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM card_sets WHERE id = ?", (card_set_id,)).fetchone()
    if not row:
        return None
    cs = CardSet(
        id=row["id"], name=row["name"], playlist_id=row["playlist_id"],
        design_id=row["design_id"], num_cards=row["num_cards"],
        show_cover_art=bool(row["show_cover_art"]), seed=row["seed"],
        cards_json=row["cards_json"], stats_json=row["stats_json"],
        pdf_path=row["pdf_path"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
    cards = [
        [Track.from_dict(t) for t in card]
        for card in json.loads(row["cards_json"])
    ]
    return cs, cards


def list_card_sets() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, playlist_id, design_id, num_cards, seed, pdf_path, created_at, stats_json "
            "FROM card_sets ORDER BY created_at DESC"
        ).fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "playlist_id": r["playlist_id"],
            "design_id": r["design_id"],
            "num_cards": r["num_cards"],
            "seed": r["seed"],
            "pdf_path": r["pdf_path"],
            "created_at": r["created_at"],
            "stats": json.loads(r["stats_json"]),
        }
        for r in rows
    ]


def update_card_set_pdf_path(card_set_id: int, pdf_path: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE card_sets SET pdf_path = ? WHERE id = ?", (pdf_path, card_set_id))


def delete_card_set(card_set_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM card_sets WHERE id = ?", (card_set_id,))
