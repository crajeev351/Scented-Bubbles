from datetime import datetime, timezone, timedelta
import pytest
from app.extensions import db
from app.models.admins import Admin
from app.models.settings import Setting
from app.services.totp_service import generate_totp_secret, get_totp_code, verify_totp


@pytest.fixture
def security_admin(app):
    """Creates a dedicated admin for security testing."""
    with app.app_context():
        admin = Admin(username="sec_admin", email="sec_admin@scentedbubbles.com", is_active=True)
        admin.set_password("AdminSecureP@ss2026")
        db.session.add(admin)
        db.session.commit()
        return admin.id


def test_admin_lockout_after_five_failed_attempts(client, app, security_admin):
    """5 consecutive failed login attempts trigger a 15-minute account lockout."""
    for attempt in range(1, 5):
        res = client.post("/admin/login", data={
            "username": "sec_admin",
            "password": "WrongPassword!",
        })
        assert res.status_code == 200
        assert b"Invalid credentials" in res.data

    # 5th failed attempt triggers lockout
    res5 = client.post("/admin/login", data={
        "username": "sec_admin",
        "password": "WrongPassword!",
    })
    assert res5.status_code == 200

    with app.app_context():
        admin = db.session.get(Admin, security_admin)
        assert admin.is_locked() is True
        assert admin.failed_login_attempts >= 5

    # 6th attempt (even with correct password) is rejected while locked
    res6 = client.post("/admin/login", data={
        "username": "sec_admin",
        "password": "AdminSecureP@ss2026",
    })
    assert res6.status_code == 200
    assert b"temporarily locked" in res6.data


def test_admin_session_inactivity_timeout(client, app, security_admin):
    """Admin sessions expire after 30 minutes of inactivity."""
    now_ts = datetime.now(timezone.utc).timestamp()

    # Active session (fresh activity)
    with client.session_transaction() as sess:
        sess["admin_id"] = security_admin
        sess["admin_username"] = "sec_admin"
        sess["admin_last_activity"] = now_ts

    res = client.get("/admin/dashboard", follow_redirects=False)
    assert res.status_code == 200

    # Inactive session (last active 31 minutes ago = 1860s)
    with client.session_transaction() as sess:
        sess["admin_id"] = security_admin
        sess["admin_username"] = "sec_admin"
        sess["admin_last_activity"] = now_ts - 1860

    res_timeout = client.get("/admin/dashboard", follow_redirects=False)
    assert res_timeout.status_code == 302
    assert "/admin/login" in res_timeout.headers["Location"]


def test_admin_totp_2fa_flow(client, app, security_admin):
    """When 2FA is active, logging in requires 6-digit TOTP verification."""
    secret = generate_totp_secret()
    with app.app_context():
        admin = db.session.get(Admin, security_admin)
        admin.totp_secret = secret
        admin.is_2fa_enabled = True
        db.session.commit()

    # Step 1: Submit username + password -> redirects to /admin/login/verify-2fa
    res_login = client.post("/admin/login", data={
        "username": "sec_admin",
        "password": "AdminSecureP@ss2026",
    }, follow_redirects=False)
    assert res_login.status_code == 302
    assert "/admin/login/verify-2fa" in res_login.headers["Location"]

    # Step 2: Submit invalid 6-digit code -> rejected
    res_invalid_2fa = client.post("/admin/login/verify-2fa", data={
        "totp_code": "000000",
    })
    assert res_invalid_2fa.status_code == 200
    assert b"Invalid 6-digit authentication code" in res_invalid_2fa.data

    # Step 3: Submit valid 6-digit code -> enters dashboard
    valid_code = get_totp_code(secret)
    res_valid_2fa = client.post("/admin/login/verify-2fa", data={
        "totp_code": valid_code,
    }, follow_redirects=False)
    assert res_valid_2fa.status_code == 302
    assert "/admin/dashboard" in res_valid_2fa.headers["Location"] or res_valid_2fa.headers["Location"].endswith("/admin/")


def test_secret_admin_slug_protection(client, app):
    """When admin_secret_slug is configured, /admin/login is obfuscated unless key matches."""
    with app.app_context():
        Setting.set_value("admin_secret_slug", "secret-vault-777")
        db.session.commit()

    # Direct access without secret key redirects to public storefront
    res_blocked = client.get("/admin/login", follow_redirects=False)
    assert res_blocked.status_code == 302
    assert res_blocked.headers["Location"] == "/"

    # Access with secret key allows viewing login screen
    res_allowed = client.get("/admin/login?key=secret-vault-777", follow_redirects=False)
    assert res_allowed.status_code == 200
    assert b"Sign In to Portal" in res_allowed.data or b"Admin" in res_allowed.data
