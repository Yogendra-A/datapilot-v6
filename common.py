"""Shared by train_grpo.py and eval.py so reward and evaluation use identical logic."""
import json
import os
import re
import sqlite3
import time

DB = os.environ.get("DB_PATH", "data/business.db")


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def to_messages(prompt: str):
    return [{"role": "user", "content": prompt}]


def extract_sql(text: str) -> str:
    """First ```sql block if present, else the raw text (stripped of a trailing ;)."""
    m = re.search(r"```sql\s*(.*?)```", text, re.S | re.I)
    sql = m.group(1) if m else text
    return sql.strip().rstrip(";").strip()


def run_readonly(sql: str, timeout_s: float = 2.0):
    """Execute a single SELECT on a read-only connection. Returns sorted rows or None."""
    if not re.match(r"^\s*select\b", sql, re.I) or ";" in sql:
        return None
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        deadline = time.time() + timeout_s
        con.set_progress_handler(lambda: 1 if time.time() > deadline else 0, 10000)
        rows = con.execute(sql).fetchall()
        con.close()
        return sorted(repr(r) for r in rows)  # order-insensitive comparison
    except Exception:
        return None


def score(completion_text: str, gold_sql: str):
    """Returns (reward, valid, correct). 1.0 correct, 0.1 valid-but-wrong, 0.0 invalid."""
    got = run_readonly(extract_sql(completion_text))
    want = run_readonly(gold_sql)
    if got is None:
        return 0.0, False, False
    if got == want:
        return 1.0, True, True
    return 0.1, True, False
