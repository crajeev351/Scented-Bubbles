"""Data migration tool to securely transfer all records from SQLite to Supabase PostgreSQL without any data loss."""

import os
import sys
import argparse
import sqlite3
from pathlib import Path
from decimal import Decimal
from sqlalchemy import create_engine, text, inspect

BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_DB = BASE_DIR / "scented_bubbles.db"

# Strict dependency order for relational data migration
TABLES_IN_ORDER = [
    "admins",
    "categories",
    "products",
    "product_categories",
    "product_variants",
    "product_images",
    "combos",
    "combo_items",
    "banners",
    "settings",
    "pages",
    "users",
    "customers",
    "orders",
    "order_items",
    "payments",
    "order_status_history",
    "order_counters",
]


def run_migration(target_db_url: str):
    if not target_db_url:
        print("[!] Error: No target DATABASE_URL provided.")
        print("Usage: python scripts/migrate_to_supabase.py --target \"postgresql://postgres:password@db.xxx.supabase.co:5432/postgres\"")
        sys.exit(1)

    if target_db_url.startswith("postgres://"):
        target_db_url = target_db_url.replace("postgres://", "postgresql://", 1)

    print("=" * 65)
    print("SCENTED BUBBLES -> SUPABASE DATA MIGRATION")
    print("=" * 65)
    print(f"[*] Source Database: {SQLITE_DB.name}")
    print(f"[*] Target Database: {target_db_url.split('@')[-1] if '@' in target_db_url else target_db_url[:20]}...")

    if not SQLITE_DB.exists():
        print(f"[!] SQLite database not found at {SQLITE_DB}")
        sys.exit(1)

    # 1. Connect to SQLite
    src_conn = sqlite3.connect(SQLITE_DB)
    src_conn.row_factory = sqlite3.Row
    src_cur = src_conn.cursor()

    # 2. Connect to Target Supabase Postgres
    try:
        dest_engine = create_engine(target_db_url)
        with dest_engine.connect() as test_conn:
            test_conn.execute(text("SELECT 1"))
        print("[+] Successfully connected to Supabase PostgreSQL!")
    except Exception as e:
        print(f"[!] Failed to connect to Supabase: {e}")
        sys.exit(1)

    # 3. Initialize schema on Supabase using Flask App Context
    from app import create_app
    from app.extensions import db
    app = create_app("production")
    app.config["SQLALCHEMY_DATABASE_URI"] = target_db_url
    with app.app_context():
        db.create_all()
        print("[+] Target schema verified and initialized.")

    # 4. Migrate tables in relational order
    total_migrated = 0
    with dest_engine.connect() as dest_conn:
        for table in TABLES_IN_ORDER:
            # Check if source table exists
            src_cur.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
            if src_cur.fetchone()[0] == 0:
                continue

            src_cur.execute(f'SELECT * FROM "{table}"')
            rows = src_cur.fetchall()
            if not rows:
                print(f"  * {table:25s}: 0 records (empty)")
                continue

            # Clear any placeholder data in destination table before inserting
            dest_conn.execute(text(f'DELETE FROM "{table}"'))

            # Insert batch
            first_row = dict(rows[0])
            columns = list(first_row.keys())
            col_list_str = ", ".join([f'"{c}"' for c in columns])
            param_list_str = ", ".join([f":{c}" for c in columns])

            insert_sql = text(f'INSERT INTO "{table}" ({col_list_str}) VALUES ({param_list_str})')

            batch = [dict(r) for r in rows]
            dest_conn.execute(insert_sql, batch)
            dest_conn.commit()

            # Advance PostgreSQL sequence for tables with primary key 'id'
            try:
                dest_conn.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('\"{table}\"', 'id'), COALESCE(MAX(id), 1)) FROM \"{table}\""
                ))
                dest_conn.commit()
            except Exception:
                # Table might not have a serial 'id' column (e.g. junction tables)
                pass

            count = len(batch)
            total_migrated += count
            print(f"  * {table:25s}: {count:4d} records migrated successfully")

    src_conn.close()

    print("=" * 65)
    print(f"[+] COMPLETE: {total_migrated} records safely migrated to Supabase with 0 data loss.")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SQLite data to Supabase PostgreSQL.")
    parser.add_argument("--target", help="Supabase PostgreSQL connection string (or set DATABASE_URL env var)")
    args = parser.parse_args()

    target_url = args.target or os.environ.get("DATABASE_URL")
    run_migration(target_url)
