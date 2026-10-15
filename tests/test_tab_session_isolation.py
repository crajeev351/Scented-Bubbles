import pytest
from app.models.admins import Admin
from app.models.users import User


def test_admin_and_customer_session_isolation(client, app):
    """Verifies that Admin and Customer sessions in different tabs do NOT invalidate each other."""
    with app.app_context():
        # Ensure test customer exists
        customer_user = User.query.filter_by(phone="9876543210").first()
        if not customer_user:
            customer_user = User(
                name="Test Customer",
                phone="9876543210",
                email="testcustomer@example.com",
                is_active=True,
            )
            customer_user.set_password("Customer@1234")
            from app.extensions import db
            db.session.add(customer_user)
            db.session.commit()

        # Ensure test admin exists
        admin_user = Admin.query.filter_by(username="admin").first()
        if not admin_user:
            admin_user = Admin(
                username="admin",
                email="admin@example.com",
                role="superadmin",
                is_active=True,
            )
            admin_user.set_password("Admin@1234")
            from app.extensions import db
            db.session.add(admin_user)
            db.session.commit()

    # Step 1: Log in as customer in "Tab 1"
    res = client.post("/account/login", data={
        "identifier": "9876543210",
        "password": "Customer@1234",
    }, follow_redirects=True)
    assert res.status_code == 200

    # Verify customer session exists
    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None
        assert sess.get("admin_id") is None

    # Step 2: Log in as admin in "Tab 2" using the same browser session
    res_admin = client.post("/admin/login", data={
        "username": "admin",
        "password": "Admin@1234",
        "keep_me_signed_in": "1",
    }, follow_redirects=True)
    assert res_admin.status_code == 200

    # Verify BOTH customer AND admin coexist without wiping each other out
    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None, "Customer session was wiped out by admin login!"
        assert sess.get("admin_id") is not None, "Admin session was not stored!"

    # Step 3: Tab 2 performs background live-sync (which triggered the instant logout before)
    res_sync = client.get("/admin/api/live-sync", headers={"X-Requested-With": "XMLHttpRequest"})
    assert res_sync.status_code == 200
    sync_data = res_sync.get_json()
    assert sync_data["success"] is True

    # Step 4: Tab 1 accesses customer orders page
    res_orders = client.get("/account/orders")
    assert res_orders.status_code == 200
    assert b"My Orders" in res_orders.data or b"Orders" in res_orders.data

    # Step 5: Customer logs out in Tab 1
    res_cust_logout = client.get("/account/logout", follow_redirects=True)
    assert res_cust_logout.status_code == 200

    # Verify Admin session is STILL ACTIVE after customer logs out!
    with client.session_transaction() as sess:
        assert sess.get("user_id") is None, "Customer session should be cleared"
        assert sess.get("admin_id") is not None, "Admin session must NOT be wiped when customer logs out!"

    # Admin live sync still works
    res_sync_after = client.get("/admin/api/live-sync", headers={"X-Requested-With": "XMLHttpRequest"})
    assert res_sync_after.status_code == 200

    # Step 6: Customer logs back in
    client.post("/account/login", data={
        "identifier": "9876543210",
        "password": "Customer@1234",
    }, follow_redirects=True)

    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None
        assert sess.get("admin_id") is not None

    # Step 7: Admin logs out in Tab 2
    res_admin_logout = client.get("/admin/logout", follow_redirects=True)
    assert res_admin_logout.status_code == 200

    # Verify Customer session is STILL ACTIVE after admin logs out!
    with client.session_transaction() as sess:
        assert sess.get("admin_id") is None, "Admin session should be cleared"
        assert sess.get("user_id") is not None, "Customer session must NOT be wiped when admin logs out!"

    # Customer orders page still accessible
    res_orders_final = client.get("/account/orders")
    assert res_orders_final.status_code == 200
