from decimal import Decimal
from unittest.mock import patch
import pytest

from app.extensions import db
from app.models.orders import Order
from app.models.payments import Payment
from app.models.users import User
from app.models.settings import Setting
from app.models.admins import Admin
from app.services.order_service import create_order
from app.services.notification_service import NotificationService


@pytest.fixture
def test_admin_user(app):
    with app.app_context():
        admin = Admin.query.filter_by(username="confirm_admin").first()
        if not admin:
            admin = Admin(username="confirm_admin", email="confirm_admin@scentedbubbles.com", is_active=True, role="superadmin")
            admin.set_password("AdminPass123!")
            db.session.add(admin)
            db.session.commit()
        return admin.id


def test_unconfirmed_order_not_visible_to_admin_until_utr_submitted(client, app, sample_catalog, test_admin_user):
    """Unless customer clicks confirm order with UTR, admin does not get order details, order registration, or email."""
    vid = sample_catalog["variant_50ml_id"]
    phone = "9876541111"

    # Register and login customer
    client.post("/account/register", data={
        "name": "Kiran Rao",
        "phone": phone,
        "email": "kiran@example.com",
        "password": "CustomerPass123!",
        "confirm_password": "CustomerPass123!",
    }, follow_redirects=True)

    with patch("app.services.notification_service.NotificationService._send_smtp_message") as mock_smtp:
        # 1. Customer initiates checkout (POST /checkout) without UTR (step 1)
        res_checkout = client.post("/checkout", data={
            "name": "Kiran Rao",
            "phone": phone,
            "email": "kiran@example.com",
            "address_line1": "Flat 502, Orchid Towers",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560001",
            "payment_method": "MANUAL_UPI",
            "items": f'[{{"variant_id": {vid}, "qty": 1}}]',
        }, follow_redirects=False)

        assert res_checkout.status_code == 302
        assert "/upi-pay" in res_checkout.headers["Location"]
        order_id = res_checkout.headers["Location"].split("/")[2]

        # Crucial Requirement: NO email sent on checkout before customer confirms with UTR!
        assert mock_smtp.call_count == 0

        # Check DB state: Order is in STATUS_AWAITING_PAYMENT and is_confirmed is False
        with app.app_context():
            ord_obj = Order.query.filter_by(order_id=order_id).first()
            assert ord_obj is not None
            assert ord_obj.is_confirmed is False
            assert ord_obj.order_status == Order.STATUS_AWAITING_PAYMENT

        # 2. Check Admin view: Admin MUST NOT see this unconfirmed order in order_list or dashboard or detail
        with client.session_transaction() as sess:
            sess["admin_id"] = test_admin_user
            sess["admin_username"] = "confirm_admin"

        # Admin order list must not show it
        res_admin_list = client.get("/admin/orders")
        assert res_admin_list.status_code == 200
        assert order_id.encode() not in res_admin_list.data

        # Admin detail must return 404 for unconfirmed order
        res_admin_detail = client.get(f"/admin/orders/{order_id}")
        assert res_admin_detail.status_code == 404

        # Admin live sync must not count it
        res_sync = client.get("/admin/api/live-sync")
        data_sync = res_sync.get_json()
        assert data_sync["latest_order_number"] != order_id

        # 3. Now Customer returns and visits upi_pay
        with client.session_transaction() as sess:
            sess.clear()
            sess["user_id"] = User.query.filter_by(phone=phone).first().id
            sess["recent_order_id"] = order_id

        # Submitting without UTR or invalid < 6 digits fails and stays on upi_pay
        res_fail = client.post(f"/orders/{order_id}/upi-pay", data={"utr": "123"}, follow_redirects=True)
        assert b"Please enter the compulsory last 6 digits" in res_fail.data

        # Submitting full 12-digit UTR automatically extracts last 6 digits and confirms order
        res_confirm = client.post(f"/orders/{order_id}/upi-pay", data={"utr": "403819823901"}, follow_redirects=True)
        assert res_confirm.status_code == 200
        assert b"Payment reference submitted" in res_confirm.data
        assert order_id.encode() in res_confirm.data

        # Verify DB state: Order is now confirmed and in STATUS_PENDING
        with app.app_context():
            refreshed = Order.query.filter_by(order_id=order_id).first()
            assert refreshed.is_confirmed is True
            assert refreshed.order_status == Order.STATUS_PENDING
            assert refreshed.latest_payment.utr == "823901"  # exactly last 6 digits!
            assert refreshed.notification_sent is True

        # Verify email was dispatched exactly upon confirmation
        assert mock_smtp.call_count >= 1

        # 4. Now Admin CAN view the order
        with client.session_transaction() as sess:
            sess["admin_id"] = test_admin_user
            sess["admin_username"] = "confirm_admin"

        res_admin_list2 = client.get("/admin/orders")
        assert order_id.encode() in res_admin_list2.data

        res_admin_detail2 = client.get(f"/admin/orders/{order_id}")
        assert res_admin_detail2.status_code == 200
        assert b"823901" in res_admin_detail2.data


def test_testing_mode_mutes_order_emails_and_prevents_duplicate_sends(app, sample_catalog):
    """Store owner can mute emails during testing, and duplicate emails are strictly prevented."""
    with app.app_context():
        vid = sample_catalog["variant_50ml_id"]
        # Enable testing mode (mute emails)
        Setting.set_value("order_notifications_enabled", "false")
        Setting.set_value("notification_email", "crajeev351@gmail.com")

        order = create_order(
            cart_items=[{"variant_id": vid, "qty": 1}],
            customer_info={"name": "Owner Testing", "phone": "9876543200", "email": "crajeev351@gmail.com"},
            shipping_info={"name": "Owner Testing", "phone": "9876543200", "address_line1": "Street 1", "city": "City", "state": "State", "pincode": "400001"},
            payment_method="MANUAL_UPI",
            utr="999888",
        )

        with patch("app.services.notification_service.NotificationService._send_smtp_message") as mock_smtp:
            # Dispatch notifications
            NotificationService.notify_order_created(order)
            # Because testing mode is muted, 0 emails are sent
            assert mock_smtp.call_count == 0

        # Now re-enable live notifications
        Setting.set_value("order_notifications_enabled", "true")
        order.notification_sent = False  # Reset flag for test

        with patch("app.services.notification_service.NotificationService._send_smtp_message") as mock_smtp:
            NotificationService.notify_order_created(order)
            # Both store owner alert AND customer order details receipt are dispatched
            assert mock_smtp.call_count == 2
            assert order.notification_sent is True

            # Attempt duplicate dispatch on same order: must be completely ignored
            NotificationService.notify_order_created(order)
            assert mock_smtp.call_count == 2


def test_customer_order_details_email_sent_only_when_registered(app, sample_catalog):
    """Verifies that customer receives rich order details email when email is registered, and skipped when no email."""
    vid = sample_catalog["variant_50ml_id"]

    with app.app_context():
        Setting.set_value("order_notifications_enabled", "true")
        Setting.set_value("notification_email", "store_owner@scentedbubbles.com")

        # 1. Customer with registered email
        with patch("app.services.notification_service.NotificationService._send_smtp_message") as mock_smtp:
            order_with_email = create_order(
                cart_items=[{"variant_id": vid, "qty": 2}],
                customer_info={"name": "Siddharth Jain", "phone": "9876543210", "email": "siddharth@example.com"},
                shipping_info={"name": "Siddharth Jain", "phone": "9876543210", "address_line1": "Road 36, Jubilee Hills", "city": "Hyderabad", "state": "Telangana", "pincode": "500033"},
                payment_method="MANUAL_UPI",
                utr="112233",
            )
            # Expect 2 emails: 1 to store owner, 1 to customer with order details
            assert mock_smtp.call_count == 2

            # Check calls
            recipients = [call.args[0] for call in mock_smtp.call_args_list]
            assert "store_owner@scentedbubbles.com" in recipients
            assert "siddharth@example.com" in recipients

            # Find customer call
            cust_call = [call for call in mock_smtp.call_args_list if call.args[0] == "siddharth@example.com"][0]
            to_email, subject, body_text = cust_call.args[0], cust_call.args[1], cust_call.args[2]
            html_body = cust_call.kwargs.get("html_body")

            assert f"#{order_with_email.order_id}" in subject
            # Plain text must contain order details
            assert order_with_email.order_id in body_text
            assert "ITEMS IN YOUR ORDER:" in body_text
            assert "Road 36, Jubilee Hills" in body_text
            assert "₹" in body_text

            # HTML body must contain rich table and styling
            assert html_body is not None
            assert order_with_email.order_id in html_body
            assert "Jubilee Hills" in html_body

        # 2. Customer without registered email (guest checkout without email)
        with patch("app.services.notification_service.NotificationService._send_smtp_message") as mock_smtp:
            order_without_email = create_order(
                cart_items=[{"variant_id": vid, "qty": 1}],
                customer_info={"name": "Phone Only User", "phone": "9988776655", "email": ""},
                shipping_info={"name": "Phone Only User", "phone": "9988776655", "address_line1": "MG Road", "city": "Bengaluru", "state": "Karnataka", "pincode": "560001"},
                payment_method="MANUAL_UPI",
                utr="445566",
            )
            # Only 1 email (to store owner), customer email is strictly skipped
            assert mock_smtp.call_count == 1
            recipients = [call.args[0] for call in mock_smtp.call_args_list]
            assert "store_owner@scentedbubbles.com" in recipients
            assert "" not in recipients


def test_business_upi_scanner_parameters(client, app, sample_catalog):
    """Verify that upi_pay page renders the QR scanner and UPI details exclusively, without 1-tap app triggers."""
    from app.services.order_service import create_order

    vid = sample_catalog["variant_50ml_id"]
    with app.app_context():
        # Set specific business settings
        Setting.set_value("upi_id", "scentedbubbles.biz@okhdfcbank")
        Setting.set_value("upi_merchant_name", "Scented Bubbles Luxury")
        Setting.set_value("upi_mcc", "5977")
        db.session.commit()

        order = create_order(
            cart_items=[{"variant_id": vid, "qty": 1}],
            customer_info={"name": "Priya Sharma", "phone": "9876543210", "email": "priya@example.com"},
            shipping_info={"name": "Priya Sharma", "phone": "9876543210", "address_line1": "Road 10", "city": "Mumbai", "state": "Maharashtra", "pincode": "400001"},
            payment_method="MANUAL_UPI",
        )
        order_id = order.order_id

    # Simulate customer visiting upi-pay screen
    with client.session_transaction() as sess:
        sess["recent_order_id"] = order_id

    res = client.get(f"/orders/{order_id}/upi-pay")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # 1. Check that Business UPI ID and Merchant details are present
    assert "scentedbubbles.biz@okhdfcbank" in html
    assert "Scented Bubbles Luxury" in html
    assert "Copy UPI ID" in html
    assert "Copy Amount" in html

    # 2. Check that QR code scanner and save button are present
    assert "upi-qr-frame" in html
    assert "upi-qr-dynamic" in html
    assert "save-qr-btn" in html
    assert "pa=scentedbubbles.biz@okhdfcbank" in html
    clean_ref = order_id.replace("-", "")
    assert f"tr={clean_ref}" in html

    # 3. Verify 1-tap app buttons and deep links are REMOVED from the page
    assert "btn-pay-gpay" not in html
    assert "com.google.android.apps.nbu.paisa.user" not in html
    assert "com.phonepe.app" not in html
    assert "net.one97.paytm" not in html
    assert "openUpiAppWithFallback" not in html


def test_admin_updates_business_upi_settings(client, app, test_admin_user):
    """Admin updates UPI ID, registered merchant name, and MCC in /admin/settings."""
    with client.session_transaction() as sess:
        sess["admin_id"] = test_admin_user
        sess["admin_username"] = "admin"

    res = client.post("/admin/settings", data={
        "company_name": "Scented Bubbles",
        "upi_id": "merchant.scented@okaxis",
        "upi_merchant_name": "Scented Bubbles Perfumes",
        "upi_mcc": "5977",
        "delivery_charge": "50.00",
        "free_delivery_threshold": "999.00",
        "cod_enabled": "false",
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        assert Setting.get_value("upi_id") == "merchant.scented@okaxis"
        assert Setting.get_value("upi_merchant_name") == "Scented Bubbles Perfumes"
        assert Setting.get_value("upi_mcc") == "5977"


def test_upi_qr_download_endpoint(client, app, sample_catalog):
    """Test same-origin qr-download route serves attachment without cross-origin redirects."""
    vid = sample_catalog["variant_50ml_id"]
    client.post("/account/register", data={
        "name": "QR Tester",
        "phone": "9876543210",
        "email": "qr@example.com",
        "password": "CustomerPass123!",
        "confirm_password": "CustomerPass123!",
    }, follow_redirects=True)

    res_checkout = client.post("/checkout", data={
        "name": "QR Tester",
        "phone": "9876543210",
        "email": "qr@example.com",
        "address_line1": "Flat 101, Test Road",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400001",
        "payment_method": "MANUAL_UPI",
        "items": f'[{{"variant_id": {vid}, "qty": 1}}]',
    }, follow_redirects=False)

    assert res_checkout.status_code == 302
    assert "/upi-pay" in res_checkout.headers["Location"]
    order_id = res_checkout.headers["Location"].split("/")[2]

    # 1. Authorized request with recent_order_id in session
    res_auth = client.get(f"/orders/{order_id}/qr-download")
    assert res_auth.status_code == 200
    assert "Content-Disposition" in res_auth.headers
    assert "attachment;" in res_auth.headers["Content-Disposition"]
    assert f"Scented_Bubbles_UPI_QR_{order_id}.png" in res_auth.headers["Content-Disposition"]
    assert res_auth.headers.get("Content-Type") in ("image/png", "image/webp", "image/jpeg")
    assert len(res_auth.data) > 100

    # 2. Unauthorized request (clear session)
    with client.session_transaction() as sess:
        sess.clear()

    res_unauth = client.get(f"/orders/{order_id}/qr-download")
    assert res_unauth.status_code == 403


