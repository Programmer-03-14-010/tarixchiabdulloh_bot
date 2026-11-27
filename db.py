# -*- coding: utf-8 -*-
import json
import re
import sqlite3
import time

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    is_admin INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grade TEXT NOT NULL, subject TEXT NOT NULL, topic TEXT NOT NULL,
    question TEXT NOT NULL, options TEXT NOT NULL, answer TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_q_path ON questions (grade, subject, topic);
CREATE TABLE IF NOT EXISTS audios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL, grade TEXT NOT NULL DEFAULT '', topic TEXT NOT NULL DEFAULT '',
    filename TEXT NOT NULL, size INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL, author TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
    filename TEXT NOT NULL, size INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL, points REAL NOT NULL, ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scores_ts ON scores (ts, user_id);
CREATE TABLE IF NOT EXISTS answer_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL, qid INTEGER NOT NULL, correct INTEGER NOT NULL, ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_log_user ON answer_log (user_id, qid, id);
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, title TEXT NOT NULL,
    qids TEXT NOT NULL, results TEXT NOT NULL DEFAULT '[]',
    started INTEGER NOT NULL, finished INTEGER NOT NULL DEFAULT 0
);
"""


def conn():
    c = sqlite3.connect(config.DB_FILE, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def norm_name(s: str) -> str:
    """Sinf/fan/mavzu nomlarida apostroflarni bir xil qiladi."""
    s = (s or "").replace("ʻ", "'").replace("‘", "'").replace("’", "'").replace("ʼ", "'").replace("`", "'")
    return re.sub(r"\s+", " ", s).strip()


def grade_key(g: str):
    m = re.search(r"\d+", g or "")
    return (int(m.group()) if m else 999, g)


def init() -> None:
    c = conn()
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript(SCHEMA)
    cols = {r["name"] for r in c.execute("PRAGMA table_info(users)")}
    for name, ddl in (
        ("username", "ALTER TABLE users ADD COLUMN username TEXT NOT NULL DEFAULT ''"),
        ("created_at", "ALTER TABLE users ADD COLUMN created_at INTEGER NOT NULL DEFAULT 0"),
    ):
        if name not in cols:
            c.execute(ddl)
    if c.execute("SELECT COUNT(*) FROM questions").fetchone()[0] == 0 and config.SEED_QUESTIONS_FILE.exists():
        data = json.loads(config.SEED_QUESTIONS_FILE.read_text(encoding="utf-8"))
        now = int(time.time())
        rows = []
        for g, subs in data.items():
            for s, topics in subs.items():
                for t, qs in topics.items():
                    for q in qs:
                        rows.append((norm_name(g), norm_name(s), norm_name(t), q["question"],
                                     json.dumps(q["options"], ensure_ascii=False), q["answer"], now))
        c.executemany(
            "INSERT INTO questions (grade, subject, topic, question, options, answer, created_at) VALUES (?,?,?,?,?,?,?)",
            rows)
    c.commit()
    c.close()


# --- foydalanuvchilar ---------------------------------------------------------
def normalize_phone(p: str) -> str:
    return "".join(ch for ch in (p or "") if ch.isdigit())


def is_admin_user(user_id: int, phone: str) -> bool:
    admins = {normalize_phone(p) for p in config.ADMIN_PHONES}
    return user_id in config.ADMIN_IDS or (normalize_phone(phone) in admins and bool(phone))


def get_user(user_id: int):
    c = conn()
    row = c.execute("SELECT * FROM users WHERE telegram_id=?", (user_id,)).fetchone()
    c.close()
    return row


def save_user(user_id: int, full_name: str, phone: str = "", username: str = "", keep_name: bool = True) -> None:
    """Foydalanuvchini yaratadi/yangilaydi. keep_name=True bo'lsa, mavjud ism-familya o'zgarmaydi."""
    c = conn()
    old = c.execute("SELECT full_name, phone FROM users WHERE telegram_id=?", (user_id,)).fetchone()
    if old:
        name = old["full_name"] if (keep_name and old["full_name"]) else full_name
        phone = phone or old["phone"]
        c.execute("UPDATE users SET full_name=?, phone=?, username=?, is_admin=? WHERE telegram_id=?",
                  (name, phone, username, int(is_admin_user(user_id, phone)), user_id))
    else:
        c.execute("INSERT INTO users (telegram_id, full_name, phone, username, is_admin, created_at) VALUES (?,?,?,?,?,?)",
                  (user_id, full_name, phone, username, int(is_admin_user(user_id, phone)), int(time.time())))
    c.commit()
    c.close()


def is_registered(user_id: int) -> bool:
    u = get_user(user_id)
    return bool(u and u["phone"])
