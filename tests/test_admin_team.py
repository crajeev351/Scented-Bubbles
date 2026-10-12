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


def test_live_sync_endpoint(client, superadmin_user):
    """Verifies the /admin/api/live-sync returns real-time counter fields."""
    with client.session_transaction() as sess:
        sess["admin_id"] = superadmin_user
        sess["admin_username"] = "super_owner"

    res = client.get("/admin/api/live-sync")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "pending_orders" in data
    assert "low_stock_count" in data
    assert "latest_order_id" in data
    assert "server_time" in data


def test_cross_admin_instant_sync(client, superadmin_user, manager_user, app):
    """Verifies that an order created or updated is immediately visible in another admin's live-sync."""
    # Manager checks initial live sync
    with client.session_transaction() as sess:
        sess["admin_id"] = manager_user
        sess["admin_username"] = "store_manager"
    res1 = client.get("/admin/api/live-sync")
    data1 = res1.get_json()
    initial_pending = data1["pending_orders"]

    # Store Owner adds a new pending order into database
    with app.app_context():
        from app.models.customers import Customer
        from decimal import Decimal
        cust = Customer(
            name="Sync Tester",
            phone="9876543210",
            email="sync@test.com",
            address_line1="123 Test Street",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
        )
        db.session.add(cust)
        db.session.flush()

        new_order = Order(
            order_id="SB-SYNC-TEST-001",
            customer_id=cust.id,
            subtotal=Decimal("599.00"),
            delivery_charge=Decimal("0.00"),
            total_amount=Decimal("599.00"),
            payment_method="COD",
            order_status=Order.STATUS_PENDING,
            shipping_name="Sync Tester",
            shipping_phone="9876543210",
            shipping_address_line1="123 Test Street",
            shipping_city="Mumbai",
            shipping_state="Maharashtra",
            shipping_pincode="400001",
        )
        db.session.add(new_order)
        db.session.commit()
        order_id = new_order.id

    # Manager queries live-sync immediately without re-login
    with client.session_transaction() as sess:
        sess["admin_id"] = manager_user
        sess["admin_username"] = "store_manager"
    res2 = client.get("/admin/api/live-sync")
    data2 = res2.get_json()

    assert data2["pending_orders"] == initial_pending + 1
    assert data2["latest_order_id"] == order_id


def test_deactivated_admin_instantly_blocked(client, superadmin_user, manager_user, app):
    """Deactivating an admin must immediately block that admin on their next request."""
    # Manager is currently logged in
    with client.session_transaction() as sess:
        sess["admin_id"] = manager_user
        sess["admin_username"] = "store_manager"

    # Superadmin deactivates the manager account in the database
    with app.app_context():
        mgr = db.session.get(Admin, manager_user)
        mgr.is_active = False
        db.session.commit()

    # Manager tries to access live-sync or any admin page
    res_api = client.get("/admin/api/live-sync")
    assert res_api.status_code == 401

    res_page = client.get("/admin/dashboard", follow_redirects=False)
    assert res_page.status_code == 302
    assert "/admin/login" in res_page.headers["Location"]
