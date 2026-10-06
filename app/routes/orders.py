from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models.orders import Order
from app.models.payments import Payment
from app.models.settings import Setting
from app.services.whatsapp_service import build_customer_whatsapp_link
from app.extensions import db

orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/orders/<order_id>/upi-pay", methods=["GET", "POST"])
def upi_pay(order_id):
    """UPI 'Scan & Pay' screen: QR code, UPI ID, exact amount, UTR submission field."""
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    
    # Store settings for UPI
    upi_id = Setting.get_value("upi_id", "scentedbubbles@upi")
    upi_qr_url = Setting.get_value("upi_qr_url", "/static/images/placeholder_upi_qr.png")
    brand_name = Setting.get_value("company_name", "Scented Bubbles")

    if request.method == "POST":
        utr = request.form.get("utr", "").strip()
        if not utr or len(utr) < 6:
            flash("Please enter a valid Bank Transaction Reference / UTR number (at least 6 digits).", "error")
            return redirect(url_for("orders.upi_pay", order_id=order_id))

        # Check UTR uniqueness across other orders
        existing_payment = Payment.query.filter(Payment.utr == utr, Payment.order_id != order.id).first()
        if existing_payment:
            flash(f"This UTR '{utr}' has already been submitted for another order.", "error")
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
                notes="UTR submitted by customer on Scan & Pay screen",
            )
            db.session.add(payment)

        db.session.commit()
        flash("Payment reference submitted! We will verify and process your order shortly.", "success")
        return redirect(url_for("orders.order_success", order_id=order.order_id))

    return render_template(
        "orders/upi_pay.html",
        order=order,
        upi_id=upi_id,
        upi_qr_url=upi_qr_url,
        brand_name=brand_name,
    )


@orders_bp.route("/orders/<order_id>/success")
def order_success(order_id):
    """Order confirmation and success page with WhatsApp notification link."""
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    
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
    from flask import session
    from app.models.users import User

    # 1. Enforce Customer Authentication
    user_id = session.get("user_id")
    if not user_id:
        flash("Please sign in to your account to view your placed order and track delivery.", "info")
        return redirect(url_for("account.login", next=request.url))

    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        session.pop("user_id", None)
        session.pop("user_name", None)
        flash("Session expired. Please sign in again.", "warning")
        return redirect(url_for("account.login"))

    # 2. Fetch ONLY current active in-progress orders (excluding DELIVERED and CANCELLED)
    current_orders = user.get_current_orders()

    # 3. Determine active order to display
    selected_order = None
    target_order_id = request.args.get("order_id", "").strip().upper()

    if target_order_id:
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

