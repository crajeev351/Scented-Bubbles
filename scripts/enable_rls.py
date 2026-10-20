"""Script to enable Row Level Security (RLS) on all public tables in Supabase PostgreSQL.

This remediates the Supabase Database Linter error 0013_rls_disabled_in_public.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

from app.config import normalize_database_url


def enable_rls(database_url: str | None = None):
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        print("[!] Error: DATABASE_URL not found.")
        sys.exit(1)

    normalized_url = normalize_database_url(url)
    engine = create_engine(normalized_url)

    print("=" * 60)
    print("ENABLING ROW LEVEL SECURITY (RLS) ON ALL PUBLIC TABLES")
    print("=" * 60)

    with engine.connect() as conn:
        # Find all user tables in public schema
        result = conn.execute(
            text(
                "SELECT tablename, rowsecurity FROM pg_tables "
                "WHERE schemaname = 'public' ORDER BY tablename;"
            )
        ).fetchall()

        if not result:
            print("[!] No tables found in public schema.")
            return

        for tablename, current_rls in result:
            if not current_rls:
                print(f"[*] Enabling RLS on public.\"{tablename}\" ...", end=" ")
                conn.execute(text(f'ALTER TABLE public."{tablename}" ENABLE ROW LEVEL SECURITY;'))
                print("DONE")
            else:
                print(f"[=] RLS already enabled on public.\"{tablename}\"")

        conn.commit()

        # Re-check status
        verification = conn.execute(
            text(
                "SELECT tablename, rowsecurity FROM pg_tables "
                "WHERE schemaname = 'public' ORDER BY tablename;"
            )
        ).fetchall()

        print("-" * 60)
        all_enabled = True
        for tablename, rls in verification:
            status = "ENABLED (SECURE)" if rls else "DISABLED (INSECURE)"
            print(f"  * {tablename:25s}: {status}")
            if not rls:
                all_enabled = False

        print("=" * 60)
        if all_enabled:
            print("[+] All tables in public schema now have Row Level Security (RLS) ENABLED!")
            print("[+] Supabase 0013_rls_disabled_in_public security lint resolved.")
        else:
            print("[!] Warning: Some tables still do not have RLS enabled.")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    enable_rls(target)
