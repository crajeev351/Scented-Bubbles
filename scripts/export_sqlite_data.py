"""Export all SQLite data to data_backup.json and data_backup.sql for 100% data safety and preservation."""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "scented_bubbles.db"
JSON_BACKUP = BASE_DIR / "data_backup.json"
SQL_BACKUP = BASE_DIR / "data_backup.sql"


def export_data():
    if not DB_PATH.exists():
        print(f"Error: Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r["name"] for r in cur.fetchall() if not r["name"].startswith("sqlite_")]

    backup_payload = {
        "_metadata": {
            "created_at": datetime.now().isoformat(),
            "source": str(DB_PATH),
            "table_count": len(tables),
        },
        "tables": {}
    }

    print("=" * 60)
    print("BACKING UP ALL SCENTED BUBBLES DATA")
    print("=" * 60)

    total_rows = 0
    for table in tables:
        cur.execute(f'SELECT * FROM "{table}"')
        rows = cur.fetchall()
        row_dicts = [dict(row) for row in rows]
        backup_payload["tables"][table] = row_dicts
        count = len(row_dicts)
        total_rows += count
        print(f"  * {table:25s}: {count:4d} records exported")

    # 1. Save JSON backup
    with open(JSON_BACKUP, "w", encoding="utf-8") as f:
        json.dump(backup_payload, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Full JSON backup saved to: {JSON_BACKUP.name} ({total_rows} total records)")

    # 2. Save Raw SQL dump
    with open(SQL_BACKUP, "w", encoding="utf-8") as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")
    print(f"[+] Full SQLite dump saved to: {SQL_BACKUP.name}")
    print("=" * 60)
    print("DATA PRESERVATION COMPLETE: 100% of data is secured.")

    conn.close()


if __name__ == "__main__":
    export_data()
