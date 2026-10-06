import os
from app import create_app
from app.extensions import db

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    with app.app_context():
        # Ensure database tables exist for local SQLite / development
        db.create_all()
        try:
            from app.models.products import Product, product_categories
            from sqlalchemy import select, insert
            with db.engine.connect() as conn:
                cnt = conn.execute(select(db.func.count()).select_from(product_categories)).scalar()
                if cnt == 0:
                    rows = conn.execute(select(Product.id, Product.category_id).where(Product.category_id.isnot(None))).all()
                    for pid, cid in rows:
                        conn.execute(insert(product_categories).values(product_id=pid, category_id=cid))
                    conn.commit()
                # Ensure inspired_by column exists across SQLite and PostgreSQL
                from sqlalchemy import inspect, text
                try:
                    inspector = inspect(db.engine)
                    if "products" in inspector.get_table_names():
                        cols = {c["name"] for c in inspector.get_columns("products")}
                        if "inspired_by" not in cols:
                            with db.engine.connect() as conn:
                                conn.execute(text("ALTER TABLE products ADD COLUMN inspired_by VARCHAR(150)"))
                                conn.commit()
                except Exception:
                    pass
        except Exception as e:
            app.logger.warning(f"Could not backfill product_categories: {e}")
    app.run(host="127.0.0.1", port=5000, debug=True)
