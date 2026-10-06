import time
from decimal import Decimal
import pytest
from sqlalchemy import event

from app.extensions import db
from app.models.admins import Admin
from app.models.orders import Order
from app.models.products import Product
from app.models.product_variants import ProductVariant
from app.models.categories import Category
from app.services import analytics_service


@pytest.fixture
def load_test_dataset(app):
    """Generates a representative load test dataset in testing database."""
    from app.cli import seed_load_test_command
    with app.app_context():
        # Create an admin user
        admin = Admin(username="analytics_admin", email="analytics@scentedbubbles.com", is_active=True)
        admin.set_password("AnalyticsPass123!")
        db.session.add(admin)
        db.session.commit()

        # Seed dataset with 30 products and 150 orders (scalable in seconds for unit test runner)
        runner = app.test_cli_runner()
        result = runner.invoke(seed_load_test_command, ["--products", "30", "--orders", "150"])
        assert result.exit_code == 0
        return admin.id


@pytest.fixture
def auth_analytics_client(client, load_test_dataset):
    with client.session_transaction() as sess:
        sess["admin_id"] = load_test_dataset
        sess["admin_username"] = "analytics_admin"
    return client


def test_analytics_service_pure_sql_aggregation(app, load_test_dataset):
    """Verify that analytics_service uses SQL aggregations only and returns aggregate data structures."""
    with app.app_context():
        # Test KPIs
        kpis = analytics_service.get_summary_kpis()
        assert "net_revenue" in kpis
        assert "total_orders" in kpis
        assert kpis["total_orders"] >= 150
        assert isinstance(kpis["net_revenue"], Decimal)

        # Test 1. Daily trend
        daily = analytics_service.get_daily_revenue_trend()
        assert "labels" in daily
        assert "revenue" in daily
        # Series length is bounded by distinct days, NOT the order count
        assert len(daily["revenue"]) == len(daily["labels"])
        assert len(daily["revenue"]) <= 180

        # Test 2. Monthly trend
        monthly = analytics_service.get_monthly_revenue_trend()
        assert len(monthly["labels"]) >= 1

        # Test 3. Order status distribution
        status_dist = analytics_service.get_orders_by_status()
        assert len(status_dist["labels"]) > 0

        # Test 4. Payment status distribution
        pay_dist = analytics_service.get_orders_by_payment_status()
        assert len(pay_dist["labels"]) > 0

        # Test 5. Top bestsellers (limit 10)
        bestsellers = analytics_service.get_top_bestsellers(10)
        assert len(bestsellers["labels"]) <= 10

        # Test 6. Category sales
        cat_sales = analytics_service.get_sales_by_category()
        assert len(cat_sales["labels"]) > 0

        # Test 7. Hourly distribution (24 bins)
        hourly = analytics_service.get_orders_by_hour()
        assert len(hourly["labels"]) <= 24


def test_analytics_and_dashboard_performance_and_query_count(app, auth_analytics_client):
    """Benchmark dashboard and analytics routes: execute quickly with bounded queries."""
    with app.app_context():
        queries = []

        def capture_queries(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)

        event.listen(db.engine, "before_cursor_execute", capture_queries)

        # 1. Test Dashboard query count & response
        queries.clear()
        t0 = time.perf_counter()
        dash_res = auth_analytics_client.get("/admin/dashboard")
        dash_time_ms = (time.perf_counter() - t0) * 1000

        assert dash_res.status_code == 200
        # Bounded query count (no N+1 loading)
        assert len(queries) < 25
        # Fast response locally (< 500ms even under test overhead)
        assert dash_time_ms < 500

        # 2. Test Analytics HTML
        queries.clear()
        t0 = time.perf_counter()
        ana_res = auth_analytics_client.get("/admin/analytics")
        ana_time_ms = (time.perf_counter() - t0) * 1000

        assert ana_res.status_code == 200
        assert len(queries) < 20
        assert ana_time_ms < 500
        # Verify Chart.js is included on analytics page
        assert "chart.umd.min.js" in ana_res.data.decode("utf-8")

        # 3. Test Analytics JSON endpoint
        queries.clear()
        t0 = time.perf_counter()
        data_res = auth_analytics_client.get("/admin/analytics/data")
        data_time_ms = (time.perf_counter() - t0) * 1000

        assert data_res.status_code == 200
        assert len(queries) < 20
        assert data_time_ms < 300
        json_data = data_res.get_json()
        assert "daily_trend" in json_data
        assert "bestsellers" in json_data

        # 4. Test Inventory view
        queries.clear()
        inv_res = auth_analytics_client.get("/admin/inventory?threshold=5")
        assert inv_res.status_code == 200
        assert len(queries) < 15

        event.remove(db.engine, "before_cursor_execute", capture_queries)


def test_cache_control_headers_and_asset_versioning(client):
    """Verify performance hardening: Cache-Control headers applied and asset_url versioning."""
    # 1. Static file Cache-Control header
    res_static = client.get("/static/css/style.css")
    assert res_static.status_code == 200
    assert "public" in res_static.headers.get("Cache-Control", "")
    assert "max-age=31536000" in res_static.headers.get("Cache-Control", "")

    # 2. Admin / Checkout / Cart never cached
    res_admin = client.get("/admin/login")
    assert res_admin.status_code == 200
    cc = res_admin.headers.get("Cache-Control", "")
    assert "no-store" in cc or "no-cache" in cc

    # 3. Public catalog response has cache revalidation header
    res_home = client.get("/")
    assert res_home.status_code == 200
    home_cc = res_home.headers.get("Cache-Control", "")
    assert "public" in home_cc
