import io
import re
from pathlib import Path
import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, Response, send_file
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
    upi_id = Setting.get_value("upi_id", "scentedbubbles@okaxis").strip()
    raw_qr = Setting.get_value("upi_qr_url", "/static/images/placeholder_upi_qr.png")
    from app.services.image_service import get_image_url
    upi_qr_url = get_image_url(raw_qr, size="medium") if raw_qr else "/static/images/placeholder_upi_qr.png"
    has_custom_qr = bool(raw_qr and not raw_qr.endswith("placeholder_upi_qr.png"))
    brand_name = Setting.get_value("company_name", "Scented Bubbles").strip()
    merchant_name = Setting.get_value("upi_merchant_name", "").strip() or brand_name
    mcc = Setting.get_value("upi_mcc", "5977").strip() or "5977"

    # Clean merchant name (NPCI: letters, numbers, spaces only, max 30 chars) and MCC
    from urllib.parse import quote_plus
    clean_brand = re.sub(r"[^\w\s]", "", merchant_name).strip()[:30] or "Scented Bubbles"
    clean_mcc = re.sub(r"\D", "", mcc)[:4] or "5977"
    # Mandatory NPCI merchant transaction reference ID (alphanumeric, max 35 chars)
    order_ref = re.sub(r"[^a-zA-Z0-9]", "", order.order_id)[:35]
    return_url = url_for("orders.upi_pay", order_id=order.order_id, _external=True)

    # Standard Clean UPI Query Parameters (omits mode=02 to avoid unsigned intent blocks on Google Pay/PhonePe)
    upi_params = (
        f"pa={upi_id}"
        f"&pn={quote_plus(clean_brand)}"
        f"&tr={order_ref}"
        f"&am={order.total_amount:.2f}"
        f"&cu=INR"
        f"&tn={quote_plus(f'Order {order.order_id}')}"
    )

    # Universal UPI URI for QR Code Generation (compliant with all UPI apps)
    upi_intent_url = f"upi://pay?{upi_params}"

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
        has_custom_qr=has_custom_qr,
        upi_intent_url=upi_intent_url,
        upi_params=upi_params,
        brand_name=brand_name,
        merchant_name=clean_brand,
        mcc=clean_mcc,
    )


@orders_bp.route("/orders/<order_id>/qr-download")
def qr_download(order_id):
    """Serve the UPI QR code as a same-origin binary download with Content-Disposition: attachment.
    Prevents cross-origin browser navigation to external storage URLs (e.g. Supabase)
    and enables direct saving to mobile galleries and downloads on Android and iOS.
    """
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    if not has_order_access(order):
        return jsonify({"error": "Unauthorized"}), 403

    raw_qr = Setting.get_value("upi_qr_url", "").strip()
    filename = f"Scented_Bubbles_UPI_QR_{order.order_id}.png"

    # 1. If merchant uploaded a custom QR code
    if raw_qr and not raw_qr.endswith("placeholder_upi_qr.png"):
        local_path = Path("app/static/uploads") / raw_qr.lstrip("/\\")
        if local_path.exists() and local_path.is_file():
            mime = "image/png"
            if str(local_path).lower().endswith(".webp"):
                mime = "image/webp"
            elif str(local_path).lower().endswith((".jpg", ".jpeg")):
                mime = "image/jpeg"
            return send_file(local_path, mimetype=mime, as_attachment=True, download_name=filename)

        from app.services.image_service import get_image_url
        full_url = get_image_url(raw_qr)
        if full_url:
            try:
                resp = requests.get(full_url, timeout=12)
                if resp.status_code == 200:
                    content_type = resp.headers.get("Content-Type", "image/png")
                    return Response(
                        resp.content,
                        mimetype=content_type,
                        headers={
                            "Content-Disposition": f'attachment; filename="{filename}"',
                            "Cache-Control": "public, max-age=3600",
                        },
                    )
            except Exception:
                pass

    # 2. Dynamic QR code or fallback: Generate PNG with NPCI UPI parameters
    upi_id = Setting.get_value("upi_id", "scentedbubbles@okaxis").strip()
    brand_name = Setting.get_value("company_name", "Scented Bubbles").strip()
    merchant_name = Setting.get_value("upi_merchant_name", "").strip() or brand_name
    from urllib.parse import quote_plus
    clean_brand = re.sub(r"[^\w\s]", "", merchant_name).strip()[:30] or "Scented Bubbles"
    order_ref = re.sub(r"[^a-zA-Z0-9]", "", order.order_id)[:35]
    upi_params = (
        f"pa={upi_id}"
        f"&pn={quote_plus(clean_brand)}"
        f"&tr={order_ref}"
        f"&am={order.total_amount:.2f}"
        f"&cu=INR"
        f"&tn={quote_plus(f'Order {order.order_id}')}"
    )
    upi_intent_url = f"upi://pay?{upi_params}"

    try:
        import qrcode
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(upi_intent_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#141312", back_color="#FFFFFF")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return Response(
            buf.getvalue(),
            mimetype="image/png",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "public, max-age=3600",
            },
        )
    except Exception:
        pass

    return redirect(url_for("orders.upi_pay", order_id=order.order_id))


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

    from app.services.notification_service import NotificationService
    customer_email = NotificationService.get_customer_email(selected_order) if selected_order else (user.email if user else "")

    return render_template(
        "orders/track.html",
        user=user,
        current_orders=current_orders,
        order=selected_order,
        customer_email=customer_email,
    )


@orders_bp.route("/orders/<order_id>/email-tracking", methods=["POST"])
def email_tracking_details(order_id):
    """Allows customer to request tracking coordinates emailed to their inbox via Resend."""
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    if not has_order_access(order):
        flash("You do not have permission to access tracking for this order.", "error")
        return redirect(url_for("account.login"))

    from app.services.notification_service import NotificationService
    customer_email = NotificationService.get_customer_email(order)
    if not customer_email:
        user_id = session.get("user_id")
        if user_id:
            u = db.session.get(User, user_id)
            if u and u.email:
                customer_email = str(u.email).strip().lower()

    if not customer_email:
        flash("No email address is linked to your order. Please contact our concierge via WhatsApp for live tracking support.", "warning")
        return redirect(url_for("orders.track_order", order_id=order.order_id))

    from app.models.settings import Setting
    brand_name = Setting.get_value("company_name", "Scented Bubbles")
    success, msg = NotificationService.send_customer_tracking_details_email(
        order, brand_name=brand_name, customer_email=customer_email, force_resend=True
    )
    if success:
        flash(f"Tracking coordinates sent to {customer_email} via Resend! Please check your inbox or spam/promotions folder.", "success")
    else:
        flash(f"Unable to send tracking email: {msg}", "error")

    referer = request.headers.get("Referer", "")
    if "account/orders" in referer:
        return redirect(url_for("account.orders"))
    return redirect(url_for("orders.track_order", order_id=order.order_id))

