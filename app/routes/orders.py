import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app.models.orders import Order
from app.models.payments import Payment
from app.models.settings import Setting
from app.models.users import User
from app.services.whatsapp_service import build_customer_whatsapp_link
from app.extensions import db

orders_bp = Blueprint("orders", __name__)


def has_order_access(order: Order) -> bool:
    """Verifies that the current session or customer is authorized to access the given order.
    Defends against Insecure Direct Object Reference (IDOR) vulnerabilities.
    """
    # 1. Admin session can access orders
    if session.get("admin_id"):
        return True

    # 2. Checkout session authorization for recently placed order
    if session.get("recent_order_id") == order.order_id:
        return True

    # 3. Authenticated customer ownership check
    user_id = session.get("user_id")
    if user_id:
        user = db.session.get(User, user_id)
        if user and user.is_active:
            user_customer_ids = [c.id for c in user.customers.all()]
            if order.customer_id and order.customer_id in user_customer_ids:
                return True
            if user.phone and order.shipping_phone == user.phone:
                return True

    return False


@orders_bp.route("/orders/<order_id>/upi-pay", methods=["GET", "POST"])
def upi_pay(order_id):
    """UPI 'Scan & Pay' screen: QR code, UPI ID, exact amount, UTR submission field."""
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    
    if not has_order_access(order):
        flash("You do not have permission to view or manage this order.", "error")
        return redirect(url_for("account.login"))

    # If already confirmed, redirect directly to success screen
    if order.is_confirmed and order.order_status != Order.STATUS_AWAITING_PAYMENT:
        return redirect(url_for("orders.order_success", order_id=order.order_id))

    # Store settings for UPI
    upi_id = Setting.get_value("upi_id", "scentedbubbles@upi")
    raw_qr = Setting.get_value("upi_qr_url", "/static/images/placeholder_upi_qr.png")
    from app.services.image_service import get_image_url
    upi_qr_url = get_image_url(raw_qr, size="medium") if raw_qr else "/static/images/placeholder_upi_qr.png"
    brand_name = Setting.get_value("company_name", "Scented Bubbles")

    # Generate specific UPI intent URLs for Google Pay (Tez), PhonePe, Paytm, and standard UPI
    from urllib.parse import quote_plus
    clean_brand = re.sub(r"[^\w\s]", "", brand_name).strip() or "Scented Bubbles"
    return_url = url_for("orders.upi_pay", order_id=order.order_id, _external=True)
    upi_params = (
        f"pa={upi_id}"
        f"&pn={quote_plus(clean_brand)}"
        f"&am={order.total_amount:.2f}"
        f"&cu=INR"
        f"&tn={quote_plus(f'Order {order.order_id}')}"
        f"&url={quote_plus(return_url)}"
    )
    upi_intent_url = f"upi://pay?{upi_params}"
    gpay_intent_url = f"tez://upi/pay?{upi_params}"
    phonepe_intent_url = f"phonepe://pay?{upi_params}"
    paytm_intent_url = f"paytmmp://pay?{upi_params}"

    if request.method == "POST":
        raw_utr = request.form.get("utr", "").strip()
        # Clean non-digits
        digits = re.sub(r"\D", "", raw_utr)

        # If user pasted 12-digit UTR, automatically extract the last 6 digits
        if len(digits) >= 6:
            digits = digits[-6:]

        if len(digits) != 6:
            flash("Please enter the compulsory last 6 digits of your UPI Bank Reference / UTR Number.", "error")
            return redirect(url_for("orders.upi_pay", order_id=order_id))

        utr = digits

        # Check UTR uniqueness across other confirmed orders
        existing_payment = Payment.query.join(Order).filter(
            Payment.utr == utr,
            Payment.order_id != order.id,
            Order.is_confirmed.is_(True),
        ).first()
        if existing_payment:
            flash(f"This UTR (last 6 digits: {utr}) has already been submitted for another order.", "error")
            return redirect(url_for("orders.upi_pay", order_id=order_id))

        # Update or create payment record
        payment = order.latest_payment
        if payment:
            payment.utr = utr
            payment.status = Payment.STATUS_PENDING_VERIFICATION
        else:
            payment = Payment(
                order_id=order.id,
                payment_method=Payment.METHOD_MANUAL_UPI,
                amount=order.total_amount,
                utr=utr,
                status=Payment.STATUS_PENDING_VERIFICATION,
                notes="UTR (last 6 digits) submitted by customer on Scan & Pay screen",
            )
            db.session.add(payment)

        # Mark order as confirmed and advance status to PENDING
        from datetime import datetime, timezone
        from app.models.order_status_history import OrderStatusHistory
        now = datetime.now(timezone.utc)
        order.is_confirmed = True
        order.confirmed_at = now
        order.order_status = Order.STATUS_PENDING

        placed_history = OrderStatusHistory(
            order_id=order.id,
            status=Order.STATUS_PENDING,
            title="Order Placed & Reference Submitted",
            notes=f"Customer verified payment with UTR (last 6 digits: {utr}). Order registered.",
            created_by="Customer",
            created_at=now,
        )
        db.session.add(placed_history)
        db.session.commit()

        # Send notifications now that order is confirmed and registered
        try:
            from app.services.notification_service import NotificationService
            NotificationService.notify_order_created(order, brand_name=brand_name)
        except Exception as notif_err:
            import logging
            logging.getLogger(__name__).warning(f"Notification error for order {order.order_id}: {notif_err}")

        flash("Payment reference submitted! Your order has been placed and registered successfully.", "success")
        return redirect(url_for("orders.order_success", order_id=order.order_id))

    return render_template(
        "orders/upi_pay.html",
        order=order,
        upi_id=upi_id,
        upi_qr_url=upi_qr_url,
        upi_intent_url=upi_intent_url,
        gpay_intent_url=gpay_intent_url,
        phonepe_intent_url=phonepe_intent_url,
        paytm_intent_url=paytm_intent_url,
        brand_name=brand_name,
    )


@orders_bp.route("/orders/<order_id>/success")
def order_success(order_id):
    """Order confirmation and success page with WhatsApp notification link."""
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    
    if not has_order_access(order):
        flash("You do not have permission to view this order confirmation.", "error")
        return redirect(url_for("account.login"))

    # Block access if order was not confirmed yet
    if not order.is_confirmed:
        flash("Please complete your payment and submit your UTR reference to confirm your order.", "warning")
        return redirect(url_for("orders.upi_pay", order_id=order.order_id))

    store_phone = Setting.get_value("support_whatsapp", "919876543210")
    brand_name = Setting.get_value("company_name", "Scented Bubbles")
    
    whatsapp_link = build_customer_whatsapp_link(order, store_phone, brand_name=brand_name)

    return render_template(
        "orders/success.html",
        order=order,
        whatsapp_link=whatsapp_link,
        brand_name=brand_name,
    )


@orders_bp.route("/track-order", methods=["GET"])
def track_order():
    """Secure order tracking: Requires customer login and displays ONLY current in-progress orders.
    Old delivered orders are excluded to conserve data and protect privacy.
    """
    # 1. Enforce Customer Authentication with clean safe redirect
    user_id = session.get("user_id")
    if not user_id:
        flash("Please sign in to your account to view your placed order and track delivery.", "info")
        return redirect(url_for("account.login", next=url_for("orders.track_order")))

    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        session.pop("user_id", None)
        session.pop("user_name", None)
        flash("Session expired. Please sign in again.", "warning")
        return redirect(url_for("account.login", next=url_for("orders.track_order")))

    # 2. Fetch ONLY current active in-progress orders (excluding DELIVERED and CANCELLED)
    current_orders = user.get_current_orders()

    # 3. Determine active order to display (sanitized order identifier)
    selected_order = None
    target_order_id = request.args.get("order_id", "").strip().upper()

    if target_order_id and re.match(r"^[A-Z0-9\-]+$", target_order_id):
        for o in current_orders:
            if o.order_id == target_order_id:
                selected_order = o
                break

    if not selected_order and current_orders:
        selected_order = current_orders[0]

    return render_template(
        "orders/track.html",
        user=user,
        current_orders=current_orders,
        order=selected_order,
    )

