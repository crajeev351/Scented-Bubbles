import uuid
import re
from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from app.models.settings import Setting
from app.services.order_service import create_order, OrderError, OutOfStockError
from app.services.payment_service import DuplicateUTRError

checkout_bp = Blueprint("checkout", __name__)


def validate_checkout_payload(data: dict) -> tuple[bool, str]:
    """Strict server-side validation for checkout inputs per security rules."""
    phone = str(data.get("phone", "")).strip()
    if not re.match(r"^[6-9]\d{9}$", phone):
        return False, "Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9."

    pincode = str(data.get("pincode", "")).strip()
    if not re.match(r"^\d{6}$", pincode):
        return False, "Please enter a valid 6-digit postal pincode."

    name = str(data.get("name", "")).strip()
    if len(name) < 2 or len(name) > 100:
        return False, "Please enter your full name (2 to 100 characters)."

    address = str(data.get("address_line1", "")).strip()
    if len(address) < 5:
        return False, "Please provide a complete delivery address."

    city = str(data.get("city", "")).strip()
    state = str(data.get("state", "")).strip()
    if not city or not state:
        return False, "City and State are required."

    email = str(data.get("email", "")).strip()
    if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        return False, "Please enter a valid email address."

    payment_method = str(data.get("payment_method", "MANUAL_UPI")).upper()
    if payment_method == "COD":
        return False, "Cash on Delivery is no longer available. Please pay securely via UPI."
    if payment_method != "MANUAL_UPI":
        return False, "Please select a valid payment method."

    return True, ""


@checkout_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    """Checkout page with login requirement, server validation, CSRF, and one-time idempotency token."""
    # Enforce customer sign-in or sign-up before proceeding to checkout
    user_id = session.get("user_id")
    if not user_id:
        if request.is_json:
            return jsonify({
                "success": False,
                "error": "Please sign in or create an account to proceed to checkout.",
                "login_required": True,
                "redirect_url": url_for("account.login", next=url_for("checkout.checkout")),
            }), 401
        flash("Please sign in or create an account to proceed to checkout.", "info")
        return redirect(url_for("account.login", next=url_for("checkout.checkout")))

    from app.models.users import User
    from app.models.customers import Customer
    from app.extensions import db
    current_user = db.session.get(User, user_id)
    if not current_user or not current_user.is_active:
        session.pop("user_id", None)
        flash("Your account session has expired. Please sign in again to proceed.", "warning")
        return redirect(url_for("account.login", next=url_for("checkout.checkout")))

    customer_profile = Customer.query.filter_by(phone=current_user.phone).first() if current_user.phone else None

    if request.method == "GET":
        # Generate new idempotency token for this checkout session
        idempotency_token = str(uuid.uuid4())
        session["checkout_idempotency_token"] = idempotency_token
        
        free_delivery_threshold = Setting.get_value("free_delivery_threshold", "999.00")
        delivery_charge = Setting.get_value("delivery_charge", "50.00")

        return render_template(
            "checkout/index.html",
            idempotency_token=idempotency_token,
            cod_enabled=False,
            current_user=current_user,
            customer_profile=customer_profile,
            free_delivery_threshold=free_delivery_threshold,
            delivery_charge=delivery_charge,
        )

    # POST request processing
    is_json = request.is_json
    data = request.get_json(silent=True) if is_json else request.form.to_dict()

    # Retrieve items
    items = data.get("items") or data.get("cart_data") or []
    if isinstance(items, str):
        import json
        try:
            items = json.loads(items)
        except Exception:
            items = []

    if not items:
        err = "Your cart is empty."
        if is_json:
            return jsonify({"success": False, "error": err}), 400
        flash(err, "error")
        return redirect(url_for("cart.view_cart"))

    # Server-side validation
    valid, err_msg = validate_checkout_payload(data)
    if not valid:
        if is_json:
            return jsonify({"success": False, "error": err_msg}), 422
        flash(err_msg, "error")
        return redirect(url_for("checkout.checkout"))

    idempotency_token = data.get("idempotency_token") or session.get("checkout_idempotency_token")
    customer_info = {
        "name": data.get("name"),
        "phone": data.get("phone"),
        "email": data.get("email"),
    }
    shipping_info = {
        "name": data.get("name"),
        "phone": data.get("phone"),
        "address_line1": data.get("address_line1"),
        "address_line2": data.get("address_line2"),
        "city": data.get("city"),
        "state": data.get("state"),
        "pincode": data.get("pincode"),
    }
    payment_method = data.get("payment_method", "MANUAL_UPI").upper()
    utr = data.get("utr", "").strip() or None
    notes = data.get("order_notes", "").strip() or None

    try:
        order = create_order(
            cart_items=items,
            customer_info=customer_info,
            shipping_info=shipping_info,
            payment_method=payment_method,
            idempotency_token=idempotency_token,
            utr=utr,
            order_notes=notes,
        )

        # Invalidate session idempotency token to prepare for next action
        session.pop("checkout_idempotency_token", None)

        # Determine target redirect
        if payment_method == "MANUAL_UPI" and not utr:
            target_url = url_for("orders.upi_pay", order_id=order.order_id)
        else:
            target_url = url_for("orders.order_success", order_id=order.order_id)

        if is_json:
            return jsonify({
                "success": True,
                "order_id": order.order_id,
                "redirect_url": target_url,
            })
        return redirect(target_url)

    except OutOfStockError as ose:
        msg = str(ose)
        if is_json:
            return jsonify({"success": False, "error": msg}), 409
        flash(msg, "error")
        return redirect(url_for("cart.view_cart"))

    except DuplicateUTRError as due:
        msg = str(due)
        if is_json:
            return jsonify({"success": False, "error": msg}), 409
        flash(msg, "error")
        return redirect(url_for("checkout.checkout"))

    except OrderError as oe:
        msg = str(oe)
        if is_json:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "error")
        return redirect(url_for("checkout.checkout"))

    except Exception as e:
        msg = "An unexpected error occurred while placing your order. Please try again."
        if is_json:
            return jsonify({"success": False, "error": msg}), 500
        flash(msg, "error")
        return redirect(url_for("checkout.checkout"))
