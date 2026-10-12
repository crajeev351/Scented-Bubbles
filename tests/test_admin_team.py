import pytest
from app.extensions import db
from app.models.admins import Admin
from app.models.orders import Order


@pytest.fixture
def superadmin_user(app):
    """Fixture creating a superadmin."""
    with app.app_context():
        admin = Admin(
            username="super_owner",
            email="owner@test.com",
            role=Admin.ROLE_SUPERADMIN,
            is_active=True,
        )
        admin.set_password("SuperPassword123!")
        db.session.add(admin)
        db.session.commit()
        return admin.id


@pytest.fixture
def manager_user(app):
    """Fixture creating a manager admin."""
    with app.app_context():
        admin = Admin(
            username="store_manager",
            email="manager@test.com",
            role=Admin.ROLE_MANAGER,
            is_active=True,
        )
        admin.set_password("ManagerPassword123!")
        db.session.add(admin)
        db.session.commit()
        return admin.id


def test_superadmin_can_access_team_page(client, superadmin_user):
    """Superadmin must be able to view the team management page."""
    with client.session_transaction() as sess:
        sess["admin_id"] = superadmin_user
        sess["admin_username"] = "super_owner"

    res = client.get("/admin/team")
    assert res.status_code == 200
    assert b"Admin Team" in res.data
    assert b"Add New Admin" in res.data


def test_manager_cannot_access_team_page(client, manager_user):
    """Manager must be redirected when trying to access admin team management."""
    with client.session_transaction() as sess:
        sess["admin_id"] = manager_user
        sess["admin_username"] = "store_manager"

    res = client.get("/admin/team", follow_redirects=False)
    assert res.status_code == 302
    assert "/admin" in res.headers["Location"]


def test_both_admins_see_shared_store_data(client, superadmin_user, manager_user, app):
    """Verify both superadmin and manager see shared business data (e.g. orders, dashboard)."""
    # Check superadmin access to dashboard
    with client.session_transaction() as sess:
        sess["admin_id"] = superadmin_user
        sess["admin_username"] = "super_owner"
    res_super = client.get("/admin/dashboard")
    assert res_super.status_code == 200

    # Check manager access to dashboard
    with client.session_transaction() as sess:
        sess["admin_id"] = manager_user
        sess["admin_username"] = "store_manager"
    res_mgr = client.get("/admin/dashboard")
    assert res_mgr.status_code == 200


def test_superadmin_creates_new_admin(client, superadmin_user, app):
    """Superadmin can create a new manager or superadmin account."""
    with client.session_transaction() as sess:
        sess["admin_id"] = superadmin_user
        sess["admin_username"] = "super_owner"

    res = client.post("/admin/team/create", data={
        "username": "co_owner2",
        "email": "coowner2@test.com",
        "display_name": "Co-Owner Two",
        "role": Admin.ROLE_SUPERADMIN,
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
    }, follow_redirects=True)

    assert res.status_code == 200
    with app.app_context():
        created = Admin.query.filter_by(username="co_owner2").first()
        assert created is not None
        assert created.role == Admin.ROLE_SUPERADMIN
        assert created.check_password("SecurePassword123!")


def test_keep_me_signed_in_flag(client, superadmin_user):
    """Logging in with keep_me_signed_in sets admin_no_timeout in session."""
    res = client.post("/admin/login", data={
        "username": "super_owner",
        "password": "SuperPassword123!",
        "keep_me_signed_in": "1",
    }, follow_redirects=False)

    assert res.status_code == 302
    with client.session_transaction() as sess:
        assert sess.get("admin_id") == superadmin_user
        assert sess.get("admin_no_timeout") is True
