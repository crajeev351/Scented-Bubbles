import os
from app import create_app
from app.extensions import db

# Determine environment (defaults to production for Render deployments)
env = os.environ.get("FLASK_ENV", "production")
app = create_app(env)

with app.app_context():
    # Automatically initialize tables in production database (e.g. Supabase PostgreSQL)
    try:
        db.create_all()
        if db.engine.dialect.name == "postgresql":
            from sqlalchemy import text
            with db.engine.connect() as conn:
                for table in db.metadata.tables.keys():
                    try:
                        conn.execute(text(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;'))
                        conn.execute(text(f'GRANT ALL ON TABLE public."{table}" TO service_role;'))
                    except Exception:
                        pass
                conn.commit()
    except Exception as e:
        app.logger.warning(f"db.create_all() warning on startup: {e}")

if __name__ == "__main__":
    app.run()
