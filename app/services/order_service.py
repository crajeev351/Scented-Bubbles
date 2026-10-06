import datetime
from datetime import timezone
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional

from sqlalchemy import update
from app.extensions import db
from app.models.customers import Customer
from app.models.orders import Order
from app.models.order_items import OrderItem
from app.models.order_counters import OrderCounter
from app.models.order_status_history import OrderStatusHistory
from app.models.product_variants import ProductVariant
from app.models.settings import Setting
from app.models.payments import Payment
from app.services.payment_service import get_payment_service, DuplicateUTRError
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class OrderError(Exception):
    """Base exception for order processing errors."""
    pass


class OutOfStockError(OrderError):
    """Raised when one or more variants have insufficient stock."""
    pass


class InvalidOrderStateError(OrderError):
    """Raised when an illegal order or payment state transition is attempted."""
    pass


def generate_order_id(session) -> str:
    """Generates an atomic, collision-free order ID in format PERF-YYYYMMDD-NNNN.
    
    Uses OrderCounter table with row-level locking (with_for_update) to guarantee
    concurrent orders on the same day receive sequential, non-colliding numbers.
    """
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    
    # Check if DB supports with_for_update (MySQL does, SQLite emulates via table lock)
    bind = session.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        counter = session.query(OrderCounter).filter_by(date_str=today_str).first()
    else:
        counter = session.query(OrderCounter).filter_by(date_str=today_str).with_for_update().first()

    if not counter:
        counter = OrderCounter(date_str=today_str, last_seq=1)
        session.add(counter)
        seq = 1
    else:
        counter.last_seq += 1
        seq = counter.last_seq
    
    session.flush()
    return f"PERF-{today_str}-{seq:04d}"


def calculate_delivery_charge(subtotal: Decimal) -> Decimal:
    """Calculates delivery charge based on store settings."""
    delivery_setting = Setting.get_value("delivery_charge", "50.00")
    free_threshold_setting = Setting.get_value("free_delivery_threshold", "999.00")

    delivery_fee = Decimal(str(delivery_setting or "50.00"))
    free_threshold = Decimal(str(free_threshold_setting or "999.00"))

    if subtotal >= free_threshold:
        return Decimal("0.00")
    return delivery_fee


def create_order(
    cart_items: List[Dict[str, Any]],
    customer_info: Dict[str, Any],
    shipping_info: Dict[str, Any],
    payment_method: str,
    idempotency_token: Optional[str] = None,
    utr: Optional[str] = None,
    order_notes: Optional[str] = None,
) -> Order:
    """Creates an order within a single atomic database transaction.
    
    BUSINESS LOGIC GUARANTEES:
    1. Idempotency: Duplicate submissions return the existing order immediately without double charging.
    2. Server-Side Pricing: Client prices are strictly ignored; prices and discounts re-fetched from DB.
    3. Stock Reservation: Decrements stock atomically inside the transaction using conditional updates.
    4. Atomic Order ID: Guaranteed uniqueness via daily counter.
    5. Snapshots: OrderItem snapshots product name, variant size, SKU, and unit price.
    6. Safe Notifications: Notification errors are logged and never abort or rollback the order.
    """
    if not cart_items:
        raise OrderError("Cart is empty.")

    # 1. Idempotency Check: if token exists, return already created order
    if idempotency_token:
        existing_order = Order.query.filter_by(idempotency_token=idempotency_token.strip()).first()
        if existing_order:
            logger.info(f"Idempotent order submit recognized: {existing_order.order_id}")
            return existing_order

    phone = str(customer_info.get("phone", "")).strip()
    if not phone or len(phone) < 10:
        raise OrderError("Valid 10-digit phone number is required.")

    # Start transactional block
    try:
        # 2. Customer match or create by phone
        customer = Customer.query.filter_by(phone=phone).first()
        if not customer:
            customer = Customer(
                phone=phone,
                name=str(customer_info.get("name") or "").strip(),
                email=str(customer_info.get("email") or "").strip() or None,
                address_line1=str(shipping_info.get("address_line1") or "").strip(),
                address_line2=str(shipping_info.get("address_line2") or "").strip() or None,
                city=str(shipping_info.get("city") or "").strip(),
                state=str(shipping_info.get("state") or "").strip(),
                pincode=str(shipping_info.get("pincode") or "").strip(),
            )
            db.session.add(customer)
            db.session.flush()
        else:
            # Update customer details
            customer.name = str(customer_info.get("name") or customer.name).strip()
            if customer_info.get("email"):
                customer.email = str(customer_info.get("email") or "").strip()
            customer.address_line1 = str(shipping_info.get("address_line1") or customer.address_line1).strip()
            customer.address_line2 = str(shipping_info.get("address_line2") or customer.address_line2 or "").strip() or None
            customer.city = str(shipping_info.get("city") or customer.city).strip()
            customer.state = str(shipping_info.get("state") or customer.state).strip()
            customer.pincode = str(shipping_info.get("pincode") or customer.pincode).strip()
            db.session.flush()

        # Link to registered user if customer profile has no user_id yet
        if not customer.user_id:
            from app.models.users import User
            matched_user = User.query.filter_by(phone=phone).first()
            if matched_user:
                customer.user_id = matched_user.id
                db.session.flush()

        # 3. Server-side variant validation, pricing, and stock reservation
        subtotal = Decimal("0.00")
        order_item_objects = []

        # Aggregate quantities if same variant is present multiple times in cart
        variant_quantities: Dict[int, int] = {}
        for item in cart_items:
            vid = int(item["variant_id"])
            qty = int(item.get("qty", 1))
            if qty <= 0:
                raise OrderError(f"Invalid quantity {qty} for variant {vid}.")
            variant_quantities[vid] = variant_quantities.get(vid, 0) + qty

        for variant_id, requested_qty in variant_quantities.items():
            # Atomically reserve stock: conditional update ensures stock >= requested_qty
            # This completely prevents negative stock and race condition overselling!
            stmt = (
                update(ProductVariant)
                .where(
                    ProductVariant.id == variant_id,
                    ProductVariant.active.is_(True),
                    ProductVariant.is_deleted.is_(False),
                    ProductVariant.stock >= requested_qty,
                )
                .values(stock=ProductVariant.stock - requested_qty)
            )
            result = db.session.execute(stmt)
            if result.rowcount == 0:
                # Either variant doesn't exist, is disabled, or stock is insufficient
                variant = db.session.get(ProductVariant, variant_id)
                var_name = f"{variant.product.name} ({variant.size_label})" if variant and variant.product else f"Variant ID {variant_id}"
                avail = variant.stock if variant else 0
                db.session.rollback()
                raise OutOfStockError(f"Insufficient stock for '{var_name}'. Available: {avail}, Requested: {requested_qty}.")

            # Fetch fresh variant details for pricing and snapshot
            variant = db.session.get(ProductVariant, variant_id)
            effective_price = variant.effective_price
            line_total = effective_price * requested_qty
            subtotal += line_total

            order_item_objects.append(
                OrderItem(
                    product_variant_id=variant.id,
                    product_name_snapshot=variant.product.name,
                    variant_label_snapshot=variant.size_label,
                    sku_snapshot=variant.sku,
                    unit_price_snapshot=effective_price,
                    quantity=requested_qty,
                    total_price=line_total,
                )
            )

        # 4. Delivery and total calculations
        delivery_charge = calculate_delivery_charge(subtotal)
        total_amount = subtotal + delivery_charge

        # 5. Generate Atomic Order ID
        atomic_order_id = generate_order_id(db.session)

        # 6. Create Order record
        order = Order(
            order_id=atomic_order_id,
            customer_id=customer.id,
            idempotency_token=idempotency_token.strip() if idempotency_token else None,
            subtotal=subtotal,
            delivery_charge=delivery_charge,
            total_amount=total_amount,
            order_status=Order.STATUS_PENDING,
            payment_status=Order.PAYMENT_PENDING_VERIFICATION,
            payment_method=payment_method.upper(),
            shipping_name=str(shipping_info.get("name") or customer.name).strip(),
            shipping_phone=str(shipping_info.get("phone") or customer.phone).strip(),
            shipping_address_line1=str(shipping_info.get("address_line1") or "").strip(),
            shipping_address_line2=str(shipping_info.get("address_line2") or "").strip() or None,
            shipping_city=str(shipping_info.get("city") or "").strip(),
            shipping_state=str(shipping_info.get("state") or "").strip(),
            shipping_pincode=str(shipping_info.get("pincode") or "").strip(),
            notes=str(order_notes or "").strip() or None,
        )
        db.session.add(order)
        db.session.flush()

        # Link order items
        for item_obj in order_item_objects:
            item_obj.order_id = order.id
            db.session.add(item_obj)

        # 7. Create Payment record through payment service
        pay_svc = get_payment_service(payment_method)
        pay_svc.create_payment(order=order, utr=utr)

        # 8. Record initial milestone history
        placed_history = OrderStatusHistory(
            order_id=order.id,
            status=Order.STATUS_PENDING,
            title="Order Placed",
            notes="Order placed by customer via checkout.",
            created_by="Customer",
            created_at=order.created_at,
        )
        db.session.add(placed_history)

        # Commit transaction
        db.session.commit()
        logger.info(f"Order {order.order_id} successfully created.")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create order: {e}")
        raise

    # 9. Notifications (safely outside transaction; failure must never fail the order)
    try:
        brand_name = Setting.get_value("company_name", "Scented Bubbles")
        NotificationService.notify_order_created(order, brand_name=brand_name)
    except Exception as notif_err:
        logger.warning(f"Notification error for order {order.order_id}: {notif_err}")

    return order


def cancel_order(order_id: str, reason: Optional[str] = None) -> Order:
    """Cancels an order and safely restores reserved stock back to variants."""
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        raise OrderError(f"Order '{order_id}' not found.")

    if not order.is_cancellable:
        raise InvalidOrderStateError(f"Cannot cancel order in status '{order.order_status}'.")

    # Restore stock for each item
    for item in order.items:
        if item.product_variant_id:
            variant = db.session.get(ProductVariant, item.product_variant_id)
            if variant:
                variant.stock += item.quantity

    now = datetime.datetime.now(timezone.utc)
    order.order_status = Order.STATUS_CANCELLED
    order.cancelled_at = now
    order.cancellation_reason = reason or "Cancelled by Admin"
    if reason:
        order.notes = f"{order.notes or ''}\nCancelled: {reason}".strip()

    # Record cancellation audit history
    cancel_hist = OrderStatusHistory(
        order_id=order.id,
        status=Order.STATUS_CANCELLED,
        title="Order Cancelled",
        notes=reason or "Order cancelled and reserved stock restored.",
        created_by="Store Admin",
        created_at=now,
    )
    db.session.add(cancel_hist)

    db.session.commit()
    logger.info(f"Order {order.order_id} cancelled and stock restored.")
    return order


def update_payment_status(order_id: str, new_status: str, admin_notes: Optional[str] = None) -> Order:
    """Updates payment status (PAID, FAILED, REFUNDED). Restores stock if payment is rejected/failed."""
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        raise OrderError(f"Order '{order_id}' not found.")

    new_status = new_status.upper()
    if new_status not in Order.PAYMENT_STATUSES:
        raise InvalidOrderStateError(f"Invalid payment status: {new_status}")

    old_status = order.payment_status
    if old_status == new_status:
        return order

    now = datetime.datetime.now(timezone.utc)

    # If transitioning to FAILED, restore stock!
    if new_status == Order.PAYMENT_FAILED and old_status != Order.PAYMENT_FAILED:
        for item in order.items:
            if item.product_variant_id:
                variant = db.session.get(ProductVariant, item.product_variant_id)
                if variant:
                    variant.stock += item.quantity
        order.order_status = Order.STATUS_CANCELLED
        order.cancelled_at = now
        order.cancellation_reason = admin_notes or "Payment verification failed"

    order.payment_status = new_status
    if order.latest_payment:
        order.latest_payment.status = new_status
        if admin_notes:
            order.latest_payment.notes = f"{order.latest_payment.notes or ''}\n{admin_notes}".strip()

    # Audit history for payment
    if new_status == Order.PAYMENT_PAID:
        order.payment_verified_at = now
        pay_hist = OrderStatusHistory(
            order_id=order.id,
            status="PAID",
            title="Payment Verified",
            notes=admin_notes or "Payment confirmed and verified in store accounts.",
            created_by="Store Admin",
            created_at=now,
        )
        db.session.add(pay_hist)

        # If payment marked PAID and order is PENDING, advance order to CONFIRMED
        if order.order_status == Order.STATUS_PENDING:
            order.order_status = Order.STATUS_CONFIRMED
            order.confirmed_at = now
            conf_hist = OrderStatusHistory(
                order_id=order.id,
                status=Order.STATUS_CONFIRMED,
                title="Order Confirmed",
                notes="Payment received. Order confirmed and queued for fulfillment.",
                created_by="System",
                created_at=now,
            )
            db.session.add(conf_hist)

    elif new_status == Order.PAYMENT_FAILED:
        fail_hist = OrderStatusHistory(
            order_id=order.id,
            status=Order.PAYMENT_FAILED,
            title="Payment Failed / Rejected",
            notes=admin_notes or "Payment verification was rejected. Stock restored.",
            created_by="Store Admin",
            created_at=now,
        )
        db.session.add(fail_hist)

    db.session.commit()
    logger.info(f"Payment status for order {order.order_id} updated from {old_status} to {new_status}.")
    return order


def update_order_status(
    order_id: str,
    new_status: str,
    courier_name: Optional[str] = None,
    tracking_number: Optional[str] = None,
    tracking_url: Optional[str] = None,
    notes: Optional[str] = None,
    operator: str = "Store Admin",
) -> Order:
    """Validates and enforces valid order state machine transitions, recording exact milestone timestamps."""
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        raise OrderError(f"Order '{order_id}' not found.")

    new_status = new_status.upper()
    if new_status not in Order.ORDER_STATUSES:
        raise InvalidOrderStateError(f"Invalid order status: {new_status}")

    # State transition validation
    allowed_transitions = {
        Order.STATUS_PENDING: [Order.STATUS_CONFIRMED, Order.STATUS_CANCELLED],
        Order.STATUS_CONFIRMED: [Order.STATUS_PACKED, Order.STATUS_CANCELLED],
        Order.STATUS_PACKED: [Order.STATUS_SHIPPED],
        Order.STATUS_SHIPPED: [Order.STATUS_DELIVERED],
        Order.STATUS_DELIVERED: [],
        Order.STATUS_CANCELLED: [],
    }

    if new_status not in allowed_transitions.get(order.order_status, []):
        raise InvalidOrderStateError(f"Cannot transition order from '{order.order_status}' to '{new_status}'.")

    if new_status == Order.STATUS_CANCELLED:
        return cancel_order(order_id, reason=notes)

    now = datetime.datetime.now(timezone.utc)
    order.order_status = new_status

    if new_status == Order.STATUS_CONFIRMED:
        order.confirmed_at = now
        title = "Order Confirmed"
        step_notes = notes or "Order confirmed and queued for fulfillment."

    elif new_status == Order.STATUS_PACKED:
        order.packed_at = now
        title = "Order Packed"
        step_notes = notes or "Items hand-inspected, prepared, and packaged for dispatch."

    elif new_status == Order.STATUS_SHIPPED:
        order.shipped_at = now
        if courier_name:
            order.courier_name = courier_name.strip()
        if tracking_number:
            order.tracking_number = tracking_number.strip()
        if tracking_url:
            order.tracking_url = tracking_url.strip()

        title = "Order Shipped"
        courier_desc = f"{order.courier_name or 'Courier'}"
        if order.tracking_number:
            courier_desc += f" (AWB: {order.tracking_number})"
        step_notes = notes or f"Shipment dispatched via {courier_desc}."

    elif new_status == Order.STATUS_DELIVERED:
        order.delivered_at = now
        title = "Delivered"
        step_notes = notes or "Shipment successfully delivered to recipient doorstep."

    else:
        title = f"Status: {new_status}"
        step_notes = notes or f"Order status transitioned to {new_status}."

    # Add audit log
    hist_entry = OrderStatusHistory(
        order_id=order.id,
        status=new_status,
        title=title,
        notes=step_notes,
        created_by=operator,
        created_at=now,
    )
    db.session.add(hist_entry)

    db.session.commit()
    logger.info(f"Order {order.order_id} advanced to {new_status} at {now.isoformat()}.")
    return order
