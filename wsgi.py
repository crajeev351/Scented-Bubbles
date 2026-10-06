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
    except Exception as e:
        app.logger.warning(f"db.create_all() warning on startup: {e}")

if __name__ == "__main__":
    app.run()
