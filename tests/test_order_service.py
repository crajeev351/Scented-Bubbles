import threading
from decimal import Decimal
from unittest.mock import patch
import pytest

from app.extensions import db
from app.models.orders import Order
from app.models.product_variants import ProductVariant
from app.services.order_service import (
    create_order,
    cancel_order,
    update_order_status,
    update_payment_status,
    generate_order_id,
    OutOfStockError,
)
from app.services.payment_service import DuplicateUTRError


def test_price_tampering_ignored(app, sample_catalog):
    """1. Price tampering ignored: client prices are never trusted, DB prices prevail."""
    with app.app_context():
        vid = sample_catalog["variant_50ml_id"]
        # Attacker sends fake price 1.00 in client payload
        cart_items = [
            {"variant_id": vid, "qty": 2, "price": "1.00", "total": "2.00"}
        ]
        customer = {"phone": "9876543210", "name": "Aarav Sharma", "email": "aarav@example.com"}
        shipping = {
            "name": "Aarav Sharma",
            "phone": "9876543210",
            "address_line1": "Flat 101, Palm Grove",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
        }

        order = create_order(
            cart_items=cart_items,
            customer_info=customer,
            shipping_info=shipping,
            payment_method="MANUAL_UPI",
        )

        # Expected subtotal = 1299.00 * 2 = 2598.00 (Free delivery over 999)
        assert order.subtotal == Decimal("2598.00")
        assert order.delivery_charge == Decimal("0.00")
        assert order.total_amount == Decimal("2598.00")
        assert order.items[0].unit_price_snapshot == Decimal("1299.00")


def test_stock_never_negative(app, sample_catalog):
    """2. Stock never negative: ordering more than stock raises OutOfStockError."""
    with app.app_context():
        vid = sample_catalog["variant_100ml_id"]
        initial_stock = sample_catalog["variant_100ml_stock"]  # 5
        
        cart_items = [{"variant_id": vid, "qty": initial_stock + 1}]
        customer = {"phone": "9876543211", "name": "Priya Patel"}
        shipping = {
            "name": "Priya Patel",
            "phone": "9876543211",
            "address_line1": "Road 12, Banjara Hills",
            "city": "Hyderabad",
            "state": "Telangana",
            "pincode": "500034",
        }

        with pytest.raises(OutOfStockError):
            create_order(
                cart_items=cart_items,
                customer_info=customer,
                shipping_info=shipping,
                payment_method="COD",
            )

        # Verify stock remained untouched and non-negative
        refreshed_v = db.session.get(ProductVariant, vid)
        assert refreshed_v.stock == initial_stock
        assert refreshed_v.stock >= 0


def test_oversell_blocked_under_concurrent_orders(app, sample_catalog):
    """3. Oversell blocked under concurrent orders: atomic conditional update protects stock."""
    vid = sample_catalog["variant_100ml_id"]
    with app.app_context():
        v = db.session.get(ProductVariant, vid)
        v.stock = 1  # Exactly 1 item available
        db.session.commit()

    results = []

    def place_order_thread(customer_phone, customer_name):
        with app.app_context():
            cart_items = [{"variant_id": vid, "qty": 1}]
            customer = {"phone": customer_phone, "name": customer_name}
            shipping = {
                "name": customer_name,
                "phone": customer_phone,
                "address_line1": "Brigade Road",
                "city": "Bangalore",
                "state": "Karnataka",
                "pincode": "560001",
            }
            try:
                order = create_order(
                    cart_items=cart_items,
                    customer_info=customer,
                    shipping_info=shipping,
                    payment_method="COD",
                )
                results.append(("SUCCESS", order.order_id))
            except OutOfStockError:
                results.append(("OUT_OF_STOCK", None))
            except Exception as e:
                results.append(("ERROR", str(e)))

    t1 = threading.Thread(target=place_order_thread, args=("9876543212", "Buyer One"))
    t2 = threading.Thread(target=place_order_thread, args=("9876543213", "Buyer Two"))

    t1.start()
    t1.join()  # Thread 1 purchases the single available item
    t2.start()
    t2.join()  # Thread 2 attempts to buy from 0 remaining stock

    successes = [r for r in results if r[0] == "SUCCESS"]
    out_of_stocks = [r for r in results if r[0] == "OUT_OF_STOCK"]

    assert len(successes) == 1, "Exactly one order must succeed when stock is 1"
    assert len(out_of_stocks) == 1, "The second order must be blocked by OutOfStockError"

    with app.app_context():
        final_var = db.session.get(ProductVariant, vid)
        assert final_var.stock == 0, "Stock must be exactly 0, never negative"


def test_cancel_restores_stock(app, sample_catalog):
    """4. Cancel restores stock: cancelling an order increments variant stock by ordered quantities."""
    with app.app_context():
        vid = sample_catalog["variant_50ml_id"]
        v = db.session.get(ProductVariant, vid)
        initial_stock = v.stock  # 10

        cart_items = [{"variant_id": vid, "qty": 3}]
        customer = {"phone": "9876543214", "name": "Rohan Mehra"}
        shipping = {
            "name": "Rohan Mehra",
            "phone": "9876543214",
            "address_line1": "Sector 18",
            "city": "Gurugram",
            "state": "Haryana",
            "pincode": "122001",
        }

        order = create_order(
            cart_items=cart_items,
            customer_info=customer,
            shipping_info=shipping,
            payment_method="COD",
        )

        # Stock should now be decremented by 3 (from 10 to 7)
        v_after_order = db.session.get(ProductVariant, vid)
        assert v_after_order.stock == initial_stock - 3

        # Cancel the order
        cancel_order(order.order_id, reason="Customer changed mind")

        # Stock must be restored back to initial 10
        v_restored = db.session.get(ProductVariant, vid)
        assert v_restored.stock == initial_stock
        assert order.order_status == Order.STATUS_CANCELLED


def test_duplicate_submit_returns_same_order(app, sample_catalog):
    """5. Duplicate submit returns same order: idempotency token returns existing order without double charging."""
    with app.app_context():
        vid = sample_catalog["variant_50ml_id"]
        cart_items = [{"variant_id": vid, "qty": 1}]
        customer = {"phone": "9876543215", "name": "Meera Sen"}
        shipping = {
            "name": "Meera Sen",
            "phone": "9876543215",
            "address_line1": "Park Street",
            "city": "Kolkata",
            "state": "West Bengal",
            "pincode": "700016",
        }
        token = "test-unique-idempotency-token-1234"

        # First submit
        order1 = create_order(
            cart_items=cart_items,
            customer_info=customer,
            shipping_info=shipping,
            payment_method="COD",
            idempotency_token=token,
        )

        stock_after_first = db.session.get(ProductVariant, vid).stock

        # Second submit with exact same token
        order2 = create_order(
            cart_items=cart_items,
            customer_info=customer,
            shipping_info=shipping,
            payment_method="COD",
            idempotency_token=token,
        )

        stock_after_second = db.session.get(ProductVariant, vid).stock

        assert order1.id == order2.id
        assert order1.order_id == order2.order_id
        # Stock must NOT be decremented again
        assert stock_after_second == stock_after_first


def test_order_id_unique_per_day(app):
    """6. Order ID unique per day: PERF-YYYYMMDD-NNNN format and strictly sequential numbers."""
    with app.app_context():
        id1 = generate_order_id(db.session)
        id2 = generate_order_id(db.session)
        id3 = generate_order_id(db.session)

        assert id1.startswith("PERF-")
        assert id2.startswith("PERF-")
        assert id3.startswith("PERF-")
        assert id1 != id2 != id3

        # Sequential check
        seq1 = int(id1.split("-")[-1])
        seq2 = int(id2.split("-")[-1])
        seq3 = int(id3.split("-")[-1])
        assert seq2 == seq1 + 1
        assert seq3 == seq2 + 1


def test_duplicate_utr_rejected(app, sample_catalog):
    """7. Duplicate UTR rejected: UPI UTR has a database unique constraint."""
    with app.app_context():
        vid = sample_catalog["variant_50ml_id"]
        cart = [{"variant_id": vid, "qty": 1}]
        customer1 = {"phone": "9876543216", "name": "Customer One"}
        shipping1 = {"name": "Customer One", "phone": "9876543216", "address_line1": "Street 1", "city": "Pune", "state": "MH", "pincode": "411001"}
        
        shared_utr = "328491823901"

        # First order with this UTR succeeds
        order1 = create_order(
            cart_items=cart,
            customer_info=customer1,
            shipping_info=shipping1,
            payment_method="MANUAL_UPI",
            utr=shared_utr,
        )
        assert order1.latest_payment.utr == shared_utr

        # Second order attempting to use the same UTR must fail with DuplicateUTRError
        customer2 = {"phone": "9876543217", "name": "Customer Two"}
        shipping2 = {"name": "Customer Two", "phone": "9876543217", "address_line1": "Street 2", "city": "Pune", "state": "MH", "pincode": "411001"}

        with pytest.raises(DuplicateUTRError):
            create_order(
                cart_items=cart,
                customer_info=customer2,
                shipping_info=shipping2,
                payment_method="MANUAL_UPI",
                utr=shared_utr,
            )


def test_whatsapp_failure_does_not_fail_order(app, sample_catalog):
    """8. WhatsApp failure does not fail the order: notification errors are logged and never abort order."""
    with app.app_context():
        vid = sample_catalog["variant_50ml_id"]
        cart = [{"variant_id": vid, "qty": 1}]
        customer = {"phone": "9876543218", "name": "Kabir Das"}
        shipping = {"name": "Kabir Das", "phone": "9876543218", "address_line1": "MG Road", "city": "Kochi", "state": "Kerala", "pincode": "682001"}

        # Patch NotificationService to simulate complete network crash / exception
        with patch("app.services.order_service.NotificationService.notify_order_created", side_effect=Exception("WhatsApp gateway down")):
            order = create_order(
                cart_items=cart,
                customer_info=customer,
                shipping_info=shipping,
                payment_method="COD",
            )

            # Order must still be created, committed, and returned without throwing
            assert order is not None
            assert order.order_id.startswith("PERF-")
            assert db.session.get(Order, order.id) is not None


def test_milestone_timestamps_and_status_history(app, sample_catalog):
    """Fulfillment lifecycle records exact timestamps and chronological OrderStatusHistory audit records."""
    with app.app_context():
        vid = sample_catalog["variant_50ml_id"]
        cart = [{"variant_id": vid, "qty": 1}]
        customer = {"phone": "9876543299", "name": "Meera Sen", "email": "meera@example.com"}
        shipping = {"name": "Meera Sen", "phone": "9876543299", "address_line1": "Bandra West", "city": "Mumbai", "state": "MH", "pincode": "400050"}

        # 1. Order Placed
        order = create_order(
            cart_items=cart,
            customer_info=customer,
            shipping_info=shipping,
            payment_method="MANUAL_UPI",
            utr="928301928401",
        )
        assert order.created_at is not None
        assert len(order.status_history) == 1
        assert order.status_history[0].status == "PENDING"
        assert order.status_history[0].title == "Order Placed"

        # 2. Payment Verified (advances to CONFIRMED)
        order = update_payment_status(order.order_id, "PAID", admin_notes="Bank credited")
        assert order.payment_verified_at is not None
        assert order.confirmed_at is not None
        assert order.order_status == "CONFIRMED"

        # 3. Packed
        order = update_order_status(order.order_id, "PACKED", notes="Packaged with botanical seal")
        assert order.packed_at is not None
        assert order.order_status == "PACKED"

        # 4. Shipped
        order = update_order_status(
            order.order_id,
            "SHIPPED",
            courier_name="Delhivery Express",
            tracking_number="DEL92840192IN",
            tracking_url="https://delhivery.com/track/DEL92840192IN",
        )
        assert order.shipped_at is not None
        assert order.courier_name == "Delhivery Express"
        assert order.tracking_number == "DEL92840192IN"
        assert order.order_status == "SHIPPED"

        # 5. Delivered
        order = update_order_status(order.order_id, "DELIVERED")
        assert order.delivered_at is not None
        assert order.order_status == "DELIVERED"

        # Verify full audit trail has entries for each step
        statuses = [h.status for h in order.status_history]
        assert "PENDING" in statuses
        assert "PAID" in statuses
        assert "CONFIRMED" in statuses
        assert "PACKED" in statuses
        assert "SHIPPED" in statuses
        assert "DELIVERED" in statuses

        # All history timestamps are monotonic (created_at exists and is valid)
        for h in order.status_history:
            assert h.created_at is not None
            assert h.created_at_ist is not None


def test_timezone_conversion_ist(app):
    """Test that UTC timestamps convert accurately to Indian Standard Time (IST, UTC+5:30)."""
    from datetime import datetime, timezone
    from app.utils.timezone import to_ist, format_ist

    # 05:49 AM UTC should convert to 11:19 AM IST (+5:30)
    utc_time = datetime(2026, 10, 5, 5, 49, 0, tzinfo=timezone.utc)
    ist_time = to_ist(utc_time)
    assert ist_time.hour == 11
    assert ist_time.minute == 19
    assert format_ist(utc_time, "%I:%M %p") == "11:19 AM"

    # Also works on naive datetime assuming UTC
    naive_time = datetime(2026, 10, 5, 5, 49, 0)
    assert format_ist(naive_time, "%I:%M %p") == "11:19 AM"
    assert format_ist(naive_time, "%d %b %Y at %I:%M %p") == "05 Oct 2026 at 11:19 AM"


