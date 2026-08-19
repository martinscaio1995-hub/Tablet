"""Persistência simples em SQLite para o dashboard: itens de conteúdo
(tendência -> ideia -> roteiro -> vídeo/imagem/música -> postado) e vendas.

Sem ORM de propósito — é um app de uso pessoal, sqlite3 puro é suficiente
e roda sem dependência extra no tablet.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from src.config import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS content_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    niche TEXT NOT NULL,
    topic TEXT NOT NULL,
    why_now TEXT NOT NULL,
    angle TEXT NOT NULL,
    product_tie_in TEXT NOT NULL DEFAULT '',
    viability_score INTEGER,
    viability_recommendation TEXT,
    viability_reasoning TEXT,
    idea TEXT,
    hook TEXT,
    narration TEXT,
    caption TEXT,
    hashtags TEXT,
    cta TEXT,
    video_path TEXT,
    image_path TEXT,
    music_path TEXT,
    status TEXT NOT NULL DEFAULT 'trend'
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    sale_date TEXT NOT NULL,
    product TEXT NOT NULL,
    revenue_cents INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    note TEXT NOT NULL DEFAULT '',
    content_item_id INTEGER REFERENCES content_items(id)
);
"""


@contextmanager
def get_conn():
    os.makedirs(os.path.dirname(config.db_path), exist_ok=True)
    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_trend(niche: str, trend: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO content_items
               (created_at, niche, topic, why_now, angle, product_tie_in, status)
               VALUES (?, ?, ?, ?, ?, ?, 'trend')""",
            (
                _now(),
                niche,
                trend["topic"],
                trend["why_now"],
                trend["angle"],
                trend.get("product_tie_in", ""),
            ),
        )
        return cur.lastrowid


def update_viability(item_id: int, score: int, recommendation: str, reasoning: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """UPDATE content_items
               SET viability_score = ?, viability_recommendation = ?,
                   viability_reasoning = ?, status = 'scored'
               WHERE id = ?""",
            (score, recommendation, reasoning, item_id),
        )


def update_script(item_id: int, idea: str, script) -> None:
    with get_conn() as conn:
        conn.execute(
            """UPDATE content_items
               SET idea = ?, hook = ?, narration = ?, caption = ?,
                   hashtags = ?, cta = ?, status = 'scripted'
               WHERE id = ?""",
            (
                idea,
                script.hook,
                script.narration,
                script.caption,
                json.dumps(script.hashtags, ensure_ascii=False),
                script.cta,
                item_id,
            ),
        )


def update_asset(item_id: int, field: str, path: str) -> None:
    if field not in ("video_path", "image_path", "music_path"):
        raise ValueError(f"campo inválido: {field}")
    status = "video_ready" if field == "video_path" else None
    with get_conn() as conn:
        if status:
            conn.execute(
                f"UPDATE content_items SET {field} = ?, status = ? WHERE id = ?",
                (path, status, item_id),
            )
        else:
            conn.execute(
                f"UPDATE content_items SET {field} = ? WHERE id = ?", (path, item_id)
            )


def mark_posted(item_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE content_items SET status = 'posted' WHERE id = ?", (item_id,)
        )


def list_content(limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM content_items ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_content(item_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM content_items WHERE id = ?", (item_id,)
        ).fetchone()
        return dict(row) if row else None


def add_sale(
    sale_date: str,
    product: str,
    revenue_cents: int,
    source: str = "manual",
    note: str = "",
    content_item_id: int | None = None,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO sales
               (created_at, sale_date, product, revenue_cents, source, note, content_item_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (_now(), sale_date, product, revenue_cents, source, note, content_item_id),
        )
        return cur.lastrowid


def list_sales(limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sales ORDER BY sale_date DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def sales_summary() -> dict:
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COALESCE(SUM(revenue_cents), 0) AS total FROM sales"
        ).fetchone()["total"]
        by_product = conn.execute(
            """SELECT product, COALESCE(SUM(revenue_cents), 0) AS total, COUNT(*) AS n
               FROM sales GROUP BY product ORDER BY total DESC"""
        ).fetchall()
        return {"total_cents": total, "by_product": [dict(r) for r in by_product]}
