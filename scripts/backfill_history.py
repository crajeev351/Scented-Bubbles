from datetime import datetime, timedelta, timezone
from app import create_app
from app.extensions import db
from app.models.orders import Order
from app.models.order_status_history import OrderStatusHistory

app = create_app()
with app.app_context():
    orders = Order.query.all()
    count = 0
    for o in orders:
        if OrderStatusHistory.query.filter_by(order_id=o.id).count() == 0:
            count += 1
            c_time = o.created_at
            
            # Step 1: Placed
            h1 = OrderStatusHistory(
                order_id=o.id,
                status=Order.STATUS_PENDING,
                title="Order Placed",
                notes="Order placed by customer via checkout.",
                created_by="Customer",
                created_at=c_time
            )
            db.session.add(h1)
            
            # Special case for order placed on Oct 4th and delivered today Oct 5th
            if o.order_id == "PERF-20261004-0001":
                o.payment_verified_at = datetime(2026, 10, 5, 10, 30, tzinfo=timezone.utc)
                o.confirmed_at = datetime(2026, 10, 5, 10, 32, tzinfo=timezone.utc)
                o.packed_at = datetime(2026, 10, 5, 10, 45, tzinfo=timezone.utc)
                o.shipped_at = datetime(2026, 10, 5, 10, 50, tzinfo=timezone.utc)
                o.courier_name = "Delhivery Express"
                o.tracking_number = "DL928374019IN"
                o.delivered_at = datetime(2026, 10, 5, 11, 0, tzinfo=timezone.utc)

                db.session.add(OrderStatusHistory(
                    order_id=o.id,
                    status="PAID",
                    title="Payment Verified",
                    notes="Payment verified via Manual UPI (UTR: 120392949212).",
                    created_by="Store Admin",
                    created_at=o.payment_verified_at
                ))
                db.session.add(OrderStatusHistory(
                    order_id=o.id,
                    status=Order.STATUS_CONFIRMED,
                    title="Order Confirmed",
                    notes="Order confirmed and queued for fulfillment.",
                    created_by="Store Admin",
                    created_at=o.confirmed_at
                ))
                db.session.add(OrderStatusHistory(
                    order_id=o.id,
                    status=Order.STATUS_PACKED,
                    title="Order Packed",
                    notes="Tam Dao (SRK) inspected and hand-packaged with IFRA safety seals.",
                    created_by="Store Admin",
                    created_at=o.packed_at
                ))
                db.session.add(OrderStatusHistory(
                    order_id=o.id,
                    status=Order.STATUS_SHIPPED,
                    title="Order Shipped",
                    notes="Handed over to Delhivery Express. AWB: DL928374019IN",
                    created_by="Store Admin",
                    created_at=o.shipped_at
                ))
                db.session.add(OrderStatusHistory(
                    order_id=o.id,
                    status=Order.STATUS_DELIVERED,
                    title="Delivered",
                    notes="Shipment successfully delivered to recipient doorstep.",
                    created_by="Store Admin",
                    created_at=o.delivered_at
                ))
                continue

            # Standard backfill for other demo orders
            if o.payment_status == Order.PAYMENT_PAID or o.order_status in (Order.STATUS_CONFIRMED, Order.STATUS_PACKED, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED):
                pay_time = c_time + timedelta(minutes=15)
                o.payment_verified_at = pay_time
                o.confirmed_at = pay_time + timedelta(minutes=5)
                db.session.add(OrderStatusHistory(
                    order_id=o.id,
                    status="PAID",
                    title="Payment Verified",
                    notes="Payment received and verified.",
                    created_by="Store Admin",
                    created_at=pay_time
                ))
                db.session.add(OrderStatusHistory(
                    order_id=o.id,
                    status=Order.STATUS_CONFIRMED,
                    title="Order Confirmed",
                    notes="Order confirmed and assigned for packaging.",
                    created_by="Store Admin",
                    created_at=o.confirmed_at
                ))
            
            if o.order_status in (Order.STATUS_PACKED, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED):
                pack_time = (o.confirmed_at or c_time) + timedelta(minutes=45)
                o.packed_at = pack_time
                db.session.add(OrderStatusHistory(
                    order_id=o.id,
                    status=Order.STATUS_PACKED,
                    title="Order Packed",
                    notes="Items inspected and safely packaged in protective bubble wrap.",
                    created_by="Store Admin",
                    created_at=pack_time
                ))
            
            if o.order_status in (Order.STATUS_SHIPPED, Order.STATUS_DELIVERED):
                ship_time = (o.packed_at or c_time) + timedelta(hours=3)
                o.shipped_at = ship_time
                if not o.courier_name:
                    o.courier_name = "BlueDart Express"
                if not o.tracking_number:
                    o.tracking_number = f"BD{o.id:04d}IN"
                db.session.add(OrderStatusHistory(
                    order_id=o.id,
                    status=Order.STATUS_SHIPPED,
                    title="Order Shipped",
                    notes=f"Handed over to {o.courier_name}. Tracking AWB: {o.tracking_number}",
                    created_by="Store Admin",
                    created_at=ship_time
                ))
            
            if o.order_status == Order.STATUS_DELIVERED:
                deliv_time = (o.shipped_at or c_time) + timedelta(days=2)
                o.delivered_at = deliv_time
                db.session.add(OrderStatusHistory(
                    order_id=o.id,
                    status=Order.STATUS_DELIVERED,
                    title="Delivered",
                    notes="Shipment successfully delivered to recipient.",
                    created_by="Store Admin",
                    created_at=o.delivered_at
                ))
            
            if o.order_status == Order.STATUS_CANCELLED:
                o.cancelled_at = c_time + timedelta(hours=1)
                db.session.add(OrderStatusHistory(
                    order_id=o.id,
                    status=Order.STATUS_CANCELLED,
                    title="Order Cancelled",
                    notes="Order cancelled and reserved stock restored.",
                    created_by="Store Admin",
                    created_at=o.cancelled_at
                ))

    db.session.commit()
    print(f"Backfill complete! Updated {count} orders.")
