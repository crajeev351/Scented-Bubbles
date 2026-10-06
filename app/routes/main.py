from flask import Blueprint, render_template, abort, Response, current_app, url_for
from sqlalchemy.orm import selectinload
from app.models.products import Product
from app.models.categories import Category
from app.models.combos import Combo
from app.models.banners import Banner
from app.models.pages import Page
from app.models.settings import Setting
from app.services.cache_service import cache

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Homepage: featured LIMIT 8, best sellers LIMIT 8, combos LIMIT 6, active banners only.
    Cached in-process for speed while invalidating immediately on admin edits.
    Uses selectinload to avoid N+1 queries.
    """
    def load_home_data():
        banners = (
            Banner.query.filter_by(active=True, is_deleted=False)
            .order_by(Banner.display_order.asc(), Banner.id.asc())
            .all()
        )
        featured_products = (
            Product.query.filter_by(active=True, featured=True, is_deleted=False)
            .options(selectinload(Product.variants), selectinload(Product.images), selectinload(Product.category))
            .limit(8)
            .all()
        )
        bestsellers = (
            Product.query.filter_by(active=True, bestseller=True, is_deleted=False)
            .options(selectinload(Product.variants), selectinload(Product.images), selectinload(Product.category))
            .limit(8)
            .all()
        )
        combos = (
            Combo.query.filter_by(active=True, is_deleted=False)
            .options(selectinload(Combo.items))
            .order_by(Combo.display_order.asc())
            .limit(6)
            .all()
        )
        categories = (
            Category.query.filter_by(active=True, is_deleted=False)
            .order_by(Category.display_order.asc())
            .all()
        )
        return {
            "banners": banners,
            "featured_products": featured_products,
            "bestsellers": bestsellers,
            "combos": combos,
            "categories": categories,
        }

    data = cache.get_or_set("home_data", load_home_data, ttl=300)
    return render_template("index.html", **data)


@main_bp.route("/about")
def about():
    """About Scented Bubbles page."""
    page = Page.query.filter_by(slug="about-us", is_active=True).first()
    return render_template("pages/about.html", page=page)


@main_bp.route("/contact")
def contact():
    """Contact page showing dynamic store details from settings."""
    return render_template("pages/contact.html")


@main_bp.route("/policies/<slug>")
def policy(slug):
    """Database-driven policy pages (shipping-policy, refund-policy, privacy-policy, terms-conditions)."""
    page = Page.query.filter_by(slug=slug, is_active=True).first_or_404()
    return render_template("pages/policy.html", page=page)


@main_bp.route("/sitemap.xml")
def sitemap():
    """Dynamic SEO sitemap.xml listing all active products, categories, combos, and pages."""
    products = Product.query.filter_by(active=True, is_deleted=False).all()
    categories = Category.query.filter_by(active=True, is_deleted=False).all()
    combos = Combo.query.filter_by(active=True, is_deleted=False).all()
    pages = Page.query.filter_by(is_active=True).all()

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    def add_url(loc, priority="0.8", changefreq="weekly"):
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{loc}</loc>")
        xml_lines.append(f"    <changefreq>{changefreq}</changefreq>")
        xml_lines.append(f"    <priority>{priority}</priority>")
        xml_lines.append("  </url>")

    base = url_for("main.index", _external=True).rstrip("/")
    add_url(f"{base}/", priority="1.0", changefreq="daily")
    add_url(f"{base}/products", priority="0.9", changefreq="daily")
    add_url(f"{base}/combos", priority="0.8", changefreq="weekly")
    add_url(f"{base}/about", priority="0.5", changefreq="monthly")
    add_url(f"{base}/contact", priority="0.5", changefreq="monthly")

    for cat in categories:
        add_url(f"{base}/categories/{cat.slug}", priority="0.8")
    for prod in products:
        add_url(f"{base}/products/{prod.slug}", priority="0.8")
    for cmb in combos:
        add_url(f"{base}/combos/{cmb.slug}", priority="0.7")
    for pg in pages:
        add_url(f"{base}/policies/{pg.slug}", priority="0.4")

    xml_lines.append("</urlset>")
    return Response("\n".join(xml_lines), mimetype="application/xml")


@main_bp.route("/robots.txt")
def robots():
    """Standard SEO robots.txt."""
    sitemap_url = url_for("main.sitemap", _external=True)
    content = f"User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /checkout\nDisallow: /orders/\nSitemap: {sitemap_url}\n"
    return Response(content, mimetype="text/plain")


@main_bp.route("/api/health")
def health_check():
    """System health check endpoint for monitoring, uptime, and database connectivity."""
    from sqlalchemy import text
    from app.extensions import db
    db_ok = False
    products_count = 0
    err_str = None
    try:
        db.session.execute(text("SELECT 1"))
        products_count = Product.query.filter_by(active=True, is_deleted=False).count()
        db_ok = True
    except Exception as exc:
        err_str = str(exc)

    return {
        "status": "ok" if db_ok else "degraded",
        "database_connected": db_ok,
        "active_products": products_count,
        "storage_backend": current_app.config.get("STORAGE_BACKEND", "local"),
        "error": err_str,
    }, (200 if db_ok else 500)

