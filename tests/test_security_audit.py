from decimal import Decimal
import pytest
from app.extensions import db
from app.models.users import User
from app.models.admins import Admin
from app.models.orders import Order
from app.models.customers import Customer
from app.models.settings import Setting
from app.services.order_service import create_order


def test_security_headers_present_on_all_responses(client):
    """Verifies that all OWASP recommended security headers are present."""
    res = client.get("/")
    assert res.status_code == 200

    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in headers.get("Permissions-Policy", "")

    # Content Security Policy
    csp = headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'self'" in csp
    assert "https://cdn.jsdelivr.net" in csp
    assert "https://fonts.googleapis.com" in csp
    assert "https://fonts.gstatic.com" in csp


def test_cache_control_on_sensitive_and_public_routes(client, app, sample_catalog):
    """Verifies sensitive user and order routes are never cached, while static/public routes are."""
    # 1. Public catalog page: allows edge revalidation
    res_pub = client.get("/")
    assert "public" in res_pub.headers.get("Cache-Control", "")

    # 2. Sensitive routes: must be strictly no-store
    sensitive_paths = ["/admin/login", "/account/login", "/cart", "/track-order"]
    for path in sensitive_paths:
        res = client.get(path)
        cc = res.headers.get("Cache-Control", "")
        assert "no-store" in cc
        assert "no-cache" in cc

    # 3. Order routes: must be strictly no-store
    res_order = client.get("/orders/PERF-20261008-0001/upi-pay")
    cc_order = res_order.headers.get("Cache-Control", "")
    assert "no-store" in cc_order


def test_asset_url_does_not_disclose_unix_timestamp(app):
    """Asset URLs should use content/mtime hashes rather than raw epoch timestamps."""
    with app.test_request_context():
        asset_fn = app.jinja_env.globals.get("asset_url")
        assert asset_fn is not None
        url = asset_fn("css/style.css")
        assert "?v=" in url
        # Ensure it's not a 10-digit unix timestamp starting with 17...
        version = url.split("?v=")[1]
        assert not (version.isdigit() and len(version) == 10 and version.startswith("17"))


def test_open_redirect_protection(client):
    """Open redirect attacks via ?next= must be safely sanitized and rejected."""
    malicious_payloads = [
        "https://evil.example.com",
        "//evil.example.com",
        "/\\evil.example.com",
        "javascript:alert(1)",
        "data:text/html;base64,PHNjcmlwdD4=",
        "http://attacker.com/steal-creds",
    ]

    for payload in malicious_payloads:
        # Customer Login
        res = client.get(f"/account/login?next={payload}")
        assert res.status_code == 200
        assert b"evil.example.com" not in res.data
        assert b"javascript:alert" not in res.data

        # Customer Register
        res_reg = client.get(f"/account/register?next={payload}")
        assert res_reg.status_code == 200
        assert b"evil.example.com" not in res_reg.data

        # Admin Login
        res_admin = client.get(f"/admin/login?next={payload}")
        assert res_admin.status_code == 200
        assert b"evil.example.com" not in res_admin.data


def test_track_order_sqli_payloads_handled_safely(client, app):
    """ZAP SQL injection boolean payloads on /track-order are rejected safely without reflection."""
    sqli_payloads = [
        "PERF-123' AND '1'='1' --",
        "PERF-123' AND '1'='2' --",
        "' OR '1'='1",
        "1; DROP TABLE orders; --",
    ]

    for payload in sqli_payloads:
        # Unauthenticated request redirects cleanly to login without reflecting SQL payload in next
        res = client.get(f"/track-order?order_id={payload}")
        assert res.status_code == 302
        assert "next=" in res.headers["Location"]
        assert "AND" not in res.headers["Location"]
        assert "DROP" not in res.headers["Location"]


def test_order_idor_authorization_protection(client, app, sample_catalog):
    """User B cannot access or submit payments for User A's order by changing the order ID."""
    with app.app_context():
        # User A
        user_a = User(name="User A", phone="9876500001", is_active=True)
        user_a.set_password("PassUserA123!")
        db.session.add(user_a)
        db.session.commit()

        # Place Order for User A
        order_a = create_order(
            cart_items=[{"variant_id": sample_catalog["variant_50ml_id"], "qty": 1}],
            customer_info={"name": "User A", "phone": "9876500001", "email": "a@example.com"},
            shipping_info={"name": "User A", "phone": "9876500001", "address_line1": "Road 1", "city": "Pune", "state": "MH", "pincode": "411001"},
            payment_method="MANUAL_UPI",
        )
        order_a_id = order_a.order_id

        # User B
        user_b = User(name="User B", phone="9876500002", is_active=True)
        user_b.set_password("PassUserB123!")
        db.session.add(user_b)
        db.session.commit()
        user_b_id = user_b.id

    # 1. Unauthenticated stranger attempts to view order_a
    res_stranger = client.get(f"/orders/{order_a_id}/upi-pay")
    assert res_stranger.status_code == 302
    assert "/account/login" in res_stranger.headers["Location"]

    res_stranger_success = client.get(f"/orders/{order_a_id}/success")
    assert res_stranger_success.status_code == 302

    # 2. User B logs in and attempts to access order_a
    with client.session_transaction() as sess:
        sess["user_id"] = user_b_id

    res_user_b = client.get(f"/orders/{order_a_id}/upi-pay")
    assert res_user_b.status_code == 302
    assert "/account/login" in res_user_b.headers["Location"]

    # 3. User B attempts to submit UTR for order_a
    post_b = client.post(f"/orders/{order_a_id}/upi-pay", data={"utr": "999888777666"})
    assert post_b.status_code == 302
    assert "/account/login" in post_b.headers["Location"]


def test_admin_login_get_requests_not_locked_out_by_rate_limiter(client):
    """GET requests to /admin/login should not trigger 429 Too Many Requests."""
    for _ in range(12):
        res = client.get("/admin/login")
        assert res.status_code == 200
