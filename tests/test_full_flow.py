from decimal import Decimal
from app.extensions import db
from app.models.orders import Order
from app.models.customers import Customer
from app.models.payments import Payment
from app.models.product_variants import ProductVariant


def test_guest_full_checkout_flow(client, sample_catalog):
    """Verifies a guest can view homepage, fetch cart summary, and complete checkout.
    Validates that Order, OrderItem, Customer, and Payment rows are properly written in the DB.
    """
    # 1. Homepage loads successfully
    res_home = client.get("/")
    assert res_home.status_code == 200
    assert b"Scented Bubbles" in res_home.data

    # 2. Product detail loads
    prod_slug = sample_catalog["product_slug"]
    prod_name = sample_catalog["product_name"]
    res_detail = client.get(f"/products/{prod_slug}")
    assert res_detail.status_code == 200
    assert prod_name.encode() in res_detail.data

    # 3. Client checks cart summary via POST /cart/summary
    vid = sample_catalog["variant_50ml_id"]
    res_summary = client.post("/cart/summary", json={
        "items": [{"variant_id": vid, "qty": 1}]
    })
    assert res_summary.status_code == 200
    summary_data = res_summary.get_json()
    assert summary_data["is_valid"] is True
    assert summary_data["subtotal"] == "1299.00"

    # 4. Guest completes checkout via POST /checkout
    checkout_payload = {
        "name": "Ananya Roy",
        "phone": "9876543299",
        "email": "ananya@example.com",
        "address_line1": "Flat 3B, Lake View Apartments",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "pincode": "600028",
        "payment_method": "MANUAL_UPI",
        "utr": "987612345678",
        "items": [{"variant_id": vid, "qty": 1}]
    }

    res_checkout = client.post("/checkout", json=checkout_payload)
    assert res_checkout.status_code == 200
    res_json = res_checkout.get_json()
    assert res_json["success"] is True
    order_id = res_json["order_id"]
    assert order_id.startswith("PERF-")

    # 5. Verify database records
    order = Order.query.filter_by(order_id=order_id).first()
    assert order is not None
    assert order.shipping_name == "Ananya Roy"
    assert order.total_amount == Decimal("1299.00")
    assert order.order_status == Order.STATUS_PENDING
    assert order.payment_status == Order.PAYMENT_PENDING_VERIFICATION

    # Check Customer record
    customer = Customer.query.filter_by(phone="9876543299").first()
    assert customer is not None
    assert customer.name == "Ananya Roy"

    # Check OrderItem snapshots
    assert len(order.items) == 1
    item = order.items[0]
    assert item.product_name_snapshot == prod_name
    assert item.variant_label_snapshot == sample_catalog["variant_50ml_size"]
    assert item.unit_price_snapshot == Decimal("1299.00")
    assert item.quantity == 1

    # Check Payment record
    assert len(order.payments) == 1
    payment = order.payments[0]
    assert payment.payment_method == Payment.METHOD_MANUAL_UPI
    assert payment.utr == "987612345678"
    assert payment.status == Payment.STATUS_PENDING_VERIFICATION

    # 6. Verify Success Page view
    res_success = client.get(f"/orders/{order_id}/success")
    assert res_success.status_code == 200
    assert order_id.encode() in res_success.data
    assert b"wa.me" in res_success.data  # WhatsApp click-to-chat button
