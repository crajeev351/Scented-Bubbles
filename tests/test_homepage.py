from sqlalchemy import event
from app.extensions import db
from app.services.cache_service import cache


def test_homepage_query_count(client, sample_catalog):
    """Measures that the homepage executes a small, fixed number of queries without N+1 query explosions.
    Subsequent hits use the in-process cache and execute 0 DB queries.
    """
    cache.clear()

    queries = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    # Attach listener to database engine
    engine = db.engine
    event.listen(engine, "before_cursor_execute", before_cursor_execute)

    try:
        # First (cold) request
        res = client.get("/")
        assert res.status_code == 200
        cold_query_count = len(queries)
        print(f"\n[Homepage Cold Query Count]: {cold_query_count}")

        # Homepage cold query count must be small (<= 15 queries for banners, categories, featured, bestsellers, combos)
        assert cold_query_count <= 15, f"Expected small fixed query count, got {cold_query_count}"

        # Second (warm/cached) request
        queries.clear()
        res_cached = client.get("/")
        assert res_cached.status_code == 200
        warm_query_count = len(queries)
        print(f"[Homepage Cached Query Count]: {warm_query_count}")

        # In-process cache must result in 0 queries on warm hit!
        assert warm_query_count == 0, f"Expected 0 queries on warm cached hit, got {warm_query_count}"

    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def test_hero_slider_multi_slide(client, app):
    """Test that homepage renders all active banners with manual controls and dots when multiple banners exist."""
    from app.models.banners import Banner
    cache.clear()

    with app.app_context():
        b1 = Banner(
            title="Artisanal Fragrance & Automotive Elegance",
            subtitle="Discover slow-crafted perfumes",
            image_key="banner_1.webp",
            display_order=1,
            active=True,
        )
        b2 = Banner(
            title="Curated Luxury Combos",
            subtitle="Pair your favorite Eau de Parfum",
            image_key="banner_2.webp",
            display_order=2,
            active=True,
        )
        db.session.add_all([b1, b2])
        db.session.commit()

    cache.clear()
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Verify slider track and controls
    assert 'class="hero-slides-track"' in html
    assert 'id="hero-prev"' in html
    assert 'id="hero-next"' in html
    assert 'id="hero-dots"' in html
    assert 'class="hero-dot active"' in html
    assert "Artisanal Fragrance" in html
    assert "Curated Luxury Combos" in html


def test_hero_slider_single_slide(client, app):
    """Test that navigation arrows and dots are hidden when only a single banner is active."""
    from app.models.banners import Banner
    cache.clear()

    with app.app_context():
        b1 = Banner(
            title="Single Exclusive Banner",
            subtitle="Luxury scents",
            image_key="banner_single.webp",
            display_order=1,
            active=True,
        )
        db.session.add(b1)
        db.session.commit()

    cache.clear()
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Slide track still renders for the single banner
    assert 'class="hero-slides-track"' in html
    assert "Single Exclusive Banner" in html
    # But navigation arrows and dots should NOT be rendered
    assert 'id="hero-prev"' not in html
    assert 'id="hero-next"' not in html
    assert 'id="hero-dots"' not in html


