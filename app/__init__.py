import os
from pathlib import Path
from flask import Flask, render_template
from app.config import config_by_name
from app.extensions import db, migrate, csrf, limiter
from app.services.cache_service import cache


def create_app(config_name=None, config_override=None):
    """Application factory for Scented Bubbles e-commerce platform."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development").lower()

    app = Flask(__name__)
    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)
    if config_override:
        app.config.update(config_override)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    # Ensure upload directory exists
    upload_path = Path(app.config.get("UPLOAD_FOLDER", "app/static/uploads"))
    upload_path.mkdir(parents=True, exist_ok=True)

    # Ensure database columns are synchronized for SQLite
    with app.app_context():
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if "banners" in inspector.get_table_names():
                existing_cols = {col["name"] for col in inspector.get_columns("banners")}
                new_cols = [
                    ("tagline", "VARCHAR(150)"),
                    ("button_text", "VARCHAR(80)"),
                    ("secondary_button_text", "VARCHAR(80)"),
                    ("secondary_button_link", "VARCHAR(255)"),
                    ("target_type", "VARCHAR(30)"),
                    ("target_id", "INTEGER"),
                    ("overlay_opacity", "INTEGER DEFAULT 55"),
                    ("image_mobile_key", "VARCHAR(255)"),
                ]
                with db.engine.connect() as conn:
                    for cname, ctype in new_cols:
                        if cname not in existing_cols:
                            conn.execute(text(f"ALTER TABLE banners ADD COLUMN {cname} {ctype}"))
                    conn.commit()
        except Exception:
            pass

    # Register CLI commands
    from app.cli import (
        create_admin_command,
        seed_demo_command,
        reprocess_images_command,
        seed_load_test_command,
        export_data_command,
        migrate_to_supabase_command,
    )
    app.cli.add_command(create_admin_command)
    app.cli.add_command(seed_demo_command)
    app.cli.add_command(reprocess_images_command)
    app.cli.add_command(seed_load_test_command)
    app.cli.add_command(export_data_command)
    app.cli.add_command(migrate_to_supabase_command)

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.products import products_bp
    from app.routes.cart import cart_bp
    from app.routes.checkout import checkout_bp
    from app.routes.orders import orders_bp
    from app.routes.admin import admin_bp
    from app.routes.account import account_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(checkout_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(account_bp)

    # Global Context Processors
    @app.context_processor
    def inject_global_data():
        """Injects brand name, current customer, and cached store settings into all Jinja templates.
        Brand name is ALWAYS read from Setting.company_name, defaulting to 'Scented Bubbles'.
        """
        from flask import session
        from app.models.settings import Setting
        from app.models.categories import Category
        from app.models.users import User

        def load_settings():
            try:
                all_s = Setting.get_all_dict()
                return all_s
            except Exception:
                return {}

        def load_nav_categories():
            try:
                return Category.query.filter_by(active=True, is_deleted=False).order_by(Category.display_order.asc()).all()
            except Exception:
                return []

        store_settings = cache.get_or_set("global_settings", load_settings, ttl=300)
        nav_categories = cache.get_or_set("nav_categories", load_nav_categories, ttl=300)
        
        # Primary requirement: Brand name must be read from company_name setting
        brand_name = store_settings.get("company_name") or "Scented Bubbles"

        current_user = None
        user_id = session.get("user_id")
        if user_id:
            try:
                current_user = db.session.get(User, user_id)
            except Exception:
                current_user = None

        return {
            "brand_name": brand_name,
            "store_settings": store_settings,
            "nav_categories": nav_categories,
            "current_user": current_user,
        }

    # Image Template Helpers
    from app.services.image_service import get_image_url, get_image_srcset

    @app.template_global("image_url")
    def image_url_global(key, size="medium"):
        return get_image_url(key, size=size)

    @app.template_global("image_srcset")
    def image_srcset_global(key):
        return get_image_srcset(key)

    # Jinja Filters
    @app.template_filter("currency")
    def currency_filter(val):
        """Formats numbers or Decimals in INR (e.g. ₹1,299.00)."""
        try:
            val_float = float(val)
            return f"₹{val_float:,.2f}"
        except (ValueError, TypeError):
            return "₹0.00"

    @app.template_filter("mask_phone")
    def mask_phone_filter(phone):
        """Masks middle digits of phone number for privacy (e.g. 98••••1210)."""
        if not phone:
            return "—"
        p = str(phone).strip()
        if len(p) >= 10:
            return f"{p[:2]}••••{p[-4:]}"
        return p

    @app.template_filter("mask_email")
    def mask_email_filter(email):
        """Masks email address characters for admin list privacy."""
        if not email:
            return "—"
        e = str(email).strip()
        if "@" in e:
            user_part, domain = e.split("@", 1)
            if len(user_part) <= 2:
                masked_user = user_part[0] + "•"
            else:
                masked_user = user_part[0] + "••••" + user_part[-1]
            return f"{masked_user}@{domain}"
        return e

    # Indian Standard Time (IST, UTC+5:30) Filters for accurate store tracking
    from app.utils.timezone import to_ist, format_ist

    @app.template_filter("ist")
    def ist_filter(dt):
        """Converts UTC datetime (aware or naive) into Indian Standard Time (IST, UTC+5:30)."""
        return to_ist(dt)

    @app.template_filter("format_dt")
    def format_dt_filter(dt, fmt="%d %b %Y at %I:%M %p"):
        """Converts UTC datetime to IST and formats cleanly."""
        return format_ist(dt, fmt)

    # Asset Versioning Helper with Auto Cache-Busting
    @app.template_global("asset_url")
    def asset_url_global(filename):
        """Appends asset version query string based on file mtime to enforce instant cache busting on update."""
        try:
            full_path = os.path.join(app.static_folder, filename.lstrip('/'))
            v = int(os.path.getmtime(full_path))
        except Exception:
            v = "2026.2"
        return f"/static/{filename.lstrip('/')}?v={v}"

    # Performance Hardening: Cache-Control Headers
    @app.after_request
    def apply_caching_headers(response):
        from flask import request
        # Static assets: 1 year cache
        if request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        # Admin, cart, checkout, tracking, account: strictly never cache
        elif request.path.startswith(("/admin", "/cart", "/checkout", "/track-order", "/account")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        # Public catalog pages: short edge revalidation
        elif response.status_code == 200 and request.method == "GET":
            response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
        return response

    @app.errorhandler(500)
    def handle_500(e):
        import traceback
        app.logger.error(f"500 Internal Error: {e}\n{traceback.format_exc()}")
        return render_template("errors/500.html"), 500

    return app
