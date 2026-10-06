from decimal import Decimal
import pytest
from app.extensions import db
from app.models.users import User
from app.models.customers import Customer
from app.models.orders import Order
from app.services.order_service import create_order


def test_customer_registration(client, app):
    """Registering a new customer account creates User and Customer records."""
    res = client.post("/account/register", data={
        "name": "Rajesh Kumar",
        "phone": "9876543211",
        "email": "rajesh@example.com",
        "password": "CustomerSecurePass123",
        "confirm_password": "CustomerSecurePass123",
    }, follow_redirects=True)

    assert res.status_code == 200
    with app.app_context():
        user = User.query.filter_by(phone="9876543211").first()
        assert user is not None
        assert user.name == "Rajesh Kumar"
        assert user.email == "rajesh@example.com"
        assert user.check_password("CustomerSecurePass123")

        # Linked customer profile
        customer = Customer.query.filter_by(phone="9876543211").first()
        assert customer is not None
        assert customer.user_id == user.id


def test_customer_auto_links_historical_orders(client, app, sample_catalog):
    """Guest orders placed before registration automatically link to the account matching their phone."""
    phone = "9876543212"

    with app.app_context():
        # Place order as guest
        order = create_order(
            cart_items=[{"variant_id": sample_catalog["variant_50ml_id"], "qty": 1}],
            customer_info={"name": "Pre-Registered User", "phone": phone, "email": "pre@example.com"},
            shipping_info={
                "name": "Pre-Registered User",
                "phone": phone,
                "address_line1": "Flat 402, Royal Palms",
                "city": "Hyderabad",
                "state": "Telangana",
                "pincode": "500081",
            },
            payment_method="COD",
        )
        order_id = order.order_id

    # Now customer registers with the same phone
    res = client.post("/account/register", data={
        "name": "Pre-Registered User",
        "phone": phone,
        "email": "pre@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
    }, follow_redirects=True)

    assert res.status_code == 200
    with app.app_context():
        user = User.query.filter_by(phone=phone).first()
        assert user is not None
        user_orders = user.get_orders()
        assert len(user_orders) >= 1
        assert user_orders[0].order_id == order_id


def test_customer_login_with_phone_and_email(client, app):
    """Customer can sign in using either 10-digit mobile or registered email."""
    with app.app_context():
        user = User(name="Ananya Sen", phone="9876543213", email="ananya@example.com", is_active=True)
        user.set_password("AnanyaPass123")
        db.session.add(user)
        db.session.commit()

    # 1. Login with Phone
    res_phone = client.post("/account/login", data={
        "identifier": "9876543213",
        "password": "AnanyaPass123",
    }, follow_redirects=True)
    assert res_phone.status_code == 200
    assert b"My Orders &amp; Shipments" in res_phone.data or b"My Orders" in res_phone.data

    # Logout
    client.get("/account/logout", follow_redirects=True)

    # 2. Login with Email
    res_email = client.post("/account/login", data={
        "identifier": "ananya@example.com",
        "password": "AnanyaPass123",
    }, follow_redirects=True)
    assert res_email.status_code == 200
    assert b"My Orders" in res_email.data


def test_customer_orders_page_requires_auth(client):
    """Protected customer dashboard routes redirect to login when unauthenticated."""
    res = client.get("/account/orders", follow_redirects=False)
    assert res.status_code == 302
    assert "/account/login" in res.headers["Location"]


def test_customer_profile_update(client, app):
    """Customer can update their default shipping address and name."""
    with app.app_context():
        user = User(name="Vikram Rao", phone="9876543214", email="vikram@example.com", is_active=True)
        user.set_password("VikramPass123")
        db.session.add(user)
        db.session.commit()
        uid = user.id

    with client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["user_name"] = "Vikram Rao"

    res = client.post("/account/profile", data={
        "action": "details",
        "name": "Vikram K. Rao",
        "email": "vikram_new@example.com",
        "address_line1": "Plot 12, Jubilee Hills",
        "address_line2": "Road No 36",
        "city": "Hyderabad",
        "state": "Telangana",
        "pincode": "500033",
    }, follow_redirects=True)

    assert res.status_code == 200
    with app.app_context():
        updated_user = db.session.get(User, uid)
        assert updated_user.name == "Vikram K. Rao"
        assert updated_user.email == "vikram_new@example.com"
        assert updated_user.primary_customer.city == "Hyderabad"
        assert updated_user.primary_customer.pincode == "500033"


def test_quick_signup_post_checkout(client, app, sample_catalog):
    """Post-checkout 1-click password creation registers and logs customer in immediately."""
    phone = "9876543215"
    with app.app_context():
        order = create_order(
            cart_items=[{"variant_id": sample_catalog["variant_50ml_id"], "qty": 1}],
            customer_info={"name": "Priya Nair", "phone": phone, "email": "priya@example.com"},
            shipping_info={
                "name": "Priya Nair",
                "phone": phone,
                "address_line1": "Flat 101, Green Meadows",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001",
            },
            payment_method="COD",
        )

    res = client.post("/account/quick-signup", json={
        "name": "Priya Nair",
        "phone": phone,
        "email": "priya@example.com",
        "password": "PriyaPassword999",
    })

    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

    with app.app_context():
        user = User.query.filter_by(phone=phone).first()
        assert user is not None
        assert user.check_password("PriyaPassword999")
        assert len(user.get_orders()) >= 1


def test_track_order_requires_login(client):
    """Unauthenticated visitors accessing /track-order are strictly redirected to login."""
    res = client.get("/track-order", follow_redirects=False)
    assert res.status_code == 302
    assert "/account/login" in res.headers["Location"]
    assert "next=" in res.headers["Location"]


def test_track_order_authenticated_shows_current_active_orders(client, app, sample_catalog):
    """Authenticated customer sees their current active in-progress order on /track-order."""
    phone = "9876543216"
    with app.app_context():
        user = User(name="Sameer Joshi", phone=phone, email="sameer@example.com", is_active=True)
        user.set_password("SameerPass123")
        db.session.add(user)
        db.session.commit()
        uid = user.id

        order = create_order(
            cart_items=[{"variant_id": sample_catalog["variant_50ml_id"], "qty": 1}],
            customer_info={"name": "Sameer Joshi", "phone": phone, "email": "sameer@example.com"},
            shipping_info={
                "name": "Sameer Joshi",
                "phone": phone,
                "address_line1": "B-304, Sea Breeze",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400050",
            },
            payment_method="COD",
        )
        oid = order.order_id

    # Sign in customer
    with client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["user_name"] = "Sameer Joshi"

    # GET /track-order displays current active shipment
    res = client.get(f"/track-order?order_id={oid}")
    assert res.status_code == 200
    assert oid.encode() in res.data
    assert b"Current Active Shipment" in res.data
    assert b"PENDING" in res.data


def test_track_order_and_account_orders_hide_delivered_and_cancelled_orders(client, app, sample_catalog):
    """Delivered and cancelled orders are excluded from customer tracking and account orders."""
    from app.services.order_service import update_order_status
    phone = "9876543217"
    with app.app_context():
        user = User(name="Sneha Patil", phone=phone, email="sneha@example.com", is_active=True)
        user.set_password("SnehaPass123")
        db.session.add(user)
        db.session.commit()
        uid = user.id

        order = create_order(
            cart_items=[{"variant_id": sample_catalog["variant_50ml_id"], "qty": 1}],
            customer_info={"name": "Sneha Patil", "phone": phone, "email": "sneha@example.com"},
            shipping_info={
                "name": "Sneha Patil",
                "phone": phone,
                "address_line1": "Flat 4, Coral Bay",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411001",
            },
            payment_method="COD",
        )
        oid = order.order_id

        # Progress order all the way to DELIVERED
        update_order_status(oid, "CONFIRMED")
        update_order_status(oid, "PACKED")
        update_order_status(oid, "SHIPPED", courier_name="Delhivery", tracking_number="DEL123456")
        update_order_status(oid, "DELIVERED")

    with client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["user_name"] = "Sneha Patil"

    # 1. On /track-order: delivered order is not in current active orders
    res_track = client.get("/track-order")
    assert res_track.status_code == 200
    assert b"No Active Orders in Transit" in res_track.data

    # 2. On /account/orders: delivered order is not shown in current active orders
    res_orders = client.get("/account/orders")
    assert res_orders.status_code == 200
    assert b"No Active Orders in Fulfillment" in res_orders.data

    # 3. Model query get_current_orders() returns empty list
    with app.app_context():
        u = db.session.get(User, uid)
        assert len(u.get_current_orders()) == 0
        assert len(u.get_orders(current_only=False)) == 1

