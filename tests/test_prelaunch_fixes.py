import pytest
from itsdangerous import URLSafeTimedSerializer
from app.extensions import db
from app.models.users import User
from app.models.customers import Customer
from app.config import normalize_database_url


def test_password_policy_enforces_minimum_8_characters(client, app):
    """Customer registration rejects passwords shorter than 8 characters."""
    # 1. 7-character password rejected
    res_short = client.post("/account/register", data={
        "name": "Short Pass User",
        "phone": "9811122233",
        "email": "short@example.com",
        "password": "Pass123",  # 7 chars
        "confirm_password": "Pass123",
    }, follow_redirects=True)

    assert res_short.status_code == 200
    assert b"Password must be at least 8 characters long." in res_short.data
    with app.app_context():
        assert User.query.filter_by(phone="9811122233").first() is None

    # 2. 8-character password accepted
    res_valid = client.post("/account/register", data={
        "name": "Valid Pass User",
        "phone": "9811122233",
        "email": "valid@example.com",
        "password": "Password1",  # 8 chars
        "confirm_password": "Password1",
    }, follow_redirects=True)

    assert res_valid.status_code == 200
    with app.app_context():
        user = User.query.filter_by(phone="9811122233").first()
        assert user is not None
        assert user.check_password("Password1")


def test_quick_signup_enforces_8_character_password(client, app):
    """Quick signup API endpoint rejects passwords with length < 8."""
    # Short password rejected
    res_short = client.post("/account/quick-signup", json={
        "name": "Quick User",
        "phone": "9822233344",
        "password": "short",
    })
    assert res_short.status_code == 400
    data = res_short.get_json()
    assert data["success"] is False
    assert "8 characters" in data["error"]

    # 8+ chars accepted
    res_valid = client.post("/account/quick-signup", json={
        "name": "Quick User",
        "phone": "9822233344",
        "password": "SecurePassword123",
    })
    assert res_valid.status_code == 200
    assert res_valid.get_json()["success"] is True


def test_profile_password_change_enforces_8_characters(client, app):
    """Updating password in profile enforces 8-character minimum."""
    with app.app_context():
        user = User(name="Profile User", phone="9833344455", email="prof@example.com", is_active=True)
        user.set_password("OldPassword123")
        db.session.add(user)
        db.session.commit()
        uid = user.id

    with client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["user_name"] = "Profile User"

    # Try setting 5-char password
    res = client.post("/account/profile", data={
        "action": "password",
        "current_password": "OldPassword123",
        "new_password": "short",
        "confirm_new_password": "short",
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"New password must be at least 8 characters long." in res.data
    with app.app_context():
        u = db.session.get(User, uid)
        assert u.check_password("OldPassword123")


def test_sanitized_health_check_endpoint(client):
    """The /api/health endpoint returns minimal sanitized status without leaking internal configs."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    # Verify sensitive/internal fields are NOT exposed
    assert "storage_backend" not in data
    assert "active_products" not in data
    assert "error" not in data


def test_checkout_honeypot_blocks_automated_bots(client, app, sample_catalog):
    """Checkout rejects submissions if anti-bot honeypot fields are filled."""
    with app.app_context():
        user = User(name="Real Buyer", phone="9844455566", is_active=True)
        user.set_password("SecurePass123")
        db.session.add(user)
        db.session.commit()
        uid = user.id

    with client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["user_name"] = "Real Buyer"

    # Form with honeypot triggered
    payload = {
        "name": "Bot Buyer",
        "phone": "9844455566",
        "pincode": "500081",
        "address_line1": "123 Bot St",
        "city": "Hyderabad",
        "state": "Telangana",
        "payment_method": "MANUAL_UPI",
        "website_hp": "http://spamsite.example.com",  # Honeypot filled by bot
        "items": [{"variant_id": sample_catalog["variant_50ml_id"], "qty": 1}],
    }
    res = client.post("/checkout", json=payload)
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False


def test_forgot_and_reset_password_flow(client, app):
    """Customer can request a password reset and successfully set a new password via timed token."""
    with app.app_context():
        user = User(name="Reset Test", phone="9855566677", email="reset@example.com", is_active=True)
        user.set_password("OriginalPassword1")
        db.session.add(user)
        db.session.commit()
        uid = user.id

    # 1. Request password reset
    res_req = client.post("/account/forgot-password", data={
        "identifier": "reset@example.com",
    }, follow_redirects=True)
    assert res_req.status_code == 200
    assert (b"Password reset instructions have been dispatched" in res_req.data or b"SMTP" in res_req.data)

    # 2. Generate valid token and reset
    s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    token = s.dumps({"user_id": uid}, salt="customer-password-reset")

    # Access reset form
    res_page = client.get(f"/account/reset-password/{token}")
    assert res_page.status_code == 200
    assert b"Set New Password" in res_page.data

    # Submit new password
    res_post = client.post(f"/account/reset-password/{token}", data={
        "password": "BrandNewPassword123",
        "confirm_password": "BrandNewPassword123",
    }, follow_redirects=True)
    assert res_post.status_code == 200
    assert b"Your password has been reset successfully" in res_post.data

    # Verify password was updated
    with app.app_context():
        u = db.session.get(User, uid)
        assert u.check_password("BrandNewPassword123")
        assert not u.check_password("OriginalPassword1")


def test_forgot_password_for_phone_only_user_renders_whatsapp_support(client, app):
    """If an account has only a phone number and no email, WhatsApp support recovery is provided."""
    with app.app_context():
        user = User(name="Phone Only User", phone="9866677788", email=None, is_active=True)
        user.set_password("SecurePass999")
        db.session.add(user)
        db.session.commit()

    res = client.post("/account/forgot-password", data={
        "identifier": "9866677788",
    })
    assert res.status_code == 200
    assert b"Mobile Account Detected" in res.data
    assert b"Chat on WhatsApp to Reset" in res.data
    assert b"wa.me" in res.data



def test_reset_password_rejects_invalid_or_expired_token(client):
    """Reset password route cleanly rejects malformed or tampered tokens."""
    res = client.get("/account/reset-password/invalid-token-12345", follow_redirects=True)
    assert res.status_code == 200
    assert b"Invalid password reset token" in res.data


def test_database_url_normalization_security(monkeypatch):
    """Database URL normalizer protects against hardcoded defaults and requires DATABASE_URL in prod."""
    # 1. In production, missing DATABASE_URL raises RuntimeError
    monkeypatch.setenv("FLASK_ENV", "production")
    with pytest.raises(RuntimeError) as exc_info:
        normalize_database_url("")
    assert "DATABASE_URL environment variable is required in production mode" in str(exc_info.value)

    # 2. In production, SQLite URL raises RuntimeError
    with pytest.raises(RuntimeError) as exc_info2:
        normalize_database_url("sqlite:///local.db")
    assert "SQLite is not supported in production mode" in str(exc_info2.value)

    # 3. Translates Supabase direct host to AWS pooler without hardcoded password
    monkeypatch.setenv("FLASK_ENV", "development")
    raw = "postgresql://myuser:secret%40pass@db.myprojref.supabase.co:5432/postgres"
    normalized = normalize_database_url(raw)
    assert "postgresql+psycopg2://" in normalized
    assert "aws-0-ap-south-1.pooler.supabase.com:5432" in normalized
    assert "myprojref" in normalized


def test_admin_smtp_settings_and_test_email(client, app):
    """Admin can view and update SMTP configuration from the admin portal."""
    from app.models.admins import Admin
    with app.app_context():
        admin = Admin.query.first()
        if not admin:
            admin = Admin(username="admin_test", email="admin@test.com", is_active=True)
            admin.set_password("AdminPass123")
            db.session.add(admin)
            db.session.commit()
        admin_id = admin.id

    with client.session_transaction() as sess:
        sess["admin_id"] = admin_id
        sess["admin_username"] = "admin_test"

    # 1. GET /admin/settings renders Section 5 with SMTP controls
    res = client.get("/admin/settings")
    assert res.status_code == 200
    assert b"Email &amp; SMTP Configuration" in res.data
    assert b"smtp_host" in res.data
    assert b"How to Setup Free Gmail App Password" in res.data
    assert b"Verify SMTP Connection" in res.data

    # 2. POST /admin/settings updates SMTP values
    res_post = client.post("/admin/settings", data={
        "company_name": "Scented Bubbles",
        "support_email": "support@scentedbubbles.com",
        "support_whatsapp": "919876543210",
        "upi_id": "test@upi",
        "delivery_charge": "50.00",
        "free_delivery_threshold": "999.00",
        "smtp_host": "smtp.testmail.com",
        "smtp_port": "587",
        "smtp_user": "owner@testmail.com",
        "smtp_password": "testpassword123",
        "notification_email": "owner@testmail.com",
        "smtp_use_tls": "true",
    }, follow_redirects=True)
    assert res_post.status_code == 200

    from app.models.settings import Setting
    from app.services.notification_service import NotificationService
    with app.app_context():
        assert Setting.get_value("smtp_host") == "smtp.testmail.com"
        assert Setting.get_value("smtp_user") == "owner@testmail.com"
        assert Setting.get_value("smtp_password") == "testpassword123"
        cfg = NotificationService.get_smtp_config()
        assert cfg["host"] == "smtp.testmail.com"
        assert cfg["user"] == "owner@testmail.com"

