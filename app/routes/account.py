import os
import re
import secrets
import urllib.parse
from functools import wraps
import requests
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    current_app,
)
from sqlalchemy import or_
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.extensions import db, limiter, csrf
from app.models.users import User
from app.models.customers import Customer
from app.models.orders import Order
from app.models.settings import Setting
from app.services.notification_service import NotificationService
from app.utils.security import get_safe_redirect_url

account_bp = Blueprint("account", __name__, url_prefix="/account")

CUSTOMER_SESSION_KEYS = (
    "user_id",
    "user_name",
    "recent_order_id",
    "checkout_idempotency_token",
)


def clear_customer_session():
    """Clears customer session keys without destroying active admin session in another tab."""
    for key in CUSTOMER_SESSION_KEYS:
        session.pop(key, None)


def customer_required(f):
    """Decorator ensuring request has an authenticated customer session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            if request.is_json:
                return jsonify({"error": "Unauthorized", "login_url": url_for("account.login")}), 401
            flash("Please sign in or create an account to view your dashboard.", "info")
            safe_next = get_safe_redirect_url(request.path, default_url="/account/orders")
            return redirect(url_for("account.login", next=safe_next))
        
        user = db.session.get(User, session["user_id"])
        if not user or not user.is_active:
            clear_customer_session()
            flash("Account session expired or account disabled.", "warning")
            return redirect(url_for("account.login"))
            
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Returns the currently logged in User instance, or None."""
    user_id = session.get("user_id")
    if user_id:
        return db.session.get(User, user_id)
    return None


@account_bp.route("/register", methods=["GET", "POST"])
@csrf.exempt
def register():
    """Customer registration route with automatic customer and historical order linking."""
    raw_next = request.args.get("next") or request.form.get("next") or ""
    next_url = get_safe_redirect_url(raw_next, default_url=url_for("account.orders"))
    clean_next = next_url if raw_next else ""

    if session.get("user_id"):
        return redirect(next_url)

    brand_name = Setting.get_value("company_name", "Scented Bubbles")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []
        if len(name) < 2:
            errors.append("Please enter your full name.")
        if not re.match(r"^[6-9]\d{9}$", phone):
            errors.append("Please enter a valid 10-digit Indian mobile number.")
        if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors.append("Please enter a valid email address.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        # Check existing user
        if phone and User.query.filter_by(phone=phone).first():
            errors.append("An account with this phone number already exists. Please sign in instead.")
        if email and User.query.filter_by(email=email).first():
            errors.append("An account with this email address already exists. Please sign in instead.")

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template(
                "account/register.html",
                name=name,
                phone=phone,
                email=email,
                brand_name=brand_name,
                next_url=clean_next,
            )

        # Create new User
        new_user = User(
            name=name,
            phone=phone,
            email=email if email else None,
            is_active=True,
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()

        # Link or create Customer profile
        customer = Customer.query.filter_by(phone=phone).first()
        if customer:
            customer.user_id = new_user.id
            if not customer.name:
                customer.name = name
            if email and not customer.email:
                customer.email = email
        else:
            customer = Customer(
                phone=phone,
                name=name,
                email=email if email else None,
                user_id=new_user.id,
            )
            db.session.add(customer)

        db.session.commit()

        # Clear previous customer session while keeping any active admin session intact
        clear_customer_session()
        session["user_id"] = new_user.id
        session["user_name"] = new_user.name or new_user.phone
        session.permanent = True

        flash(f"Welcome to {brand_name}, {new_user.name}! Your account has been created.", "success")
        return redirect(next_url)

    return render_template("account/register.html", brand_name=brand_name, next_url=clean_next)


@account_bp.route("/login", methods=["GET", "POST"])
@csrf.exempt
@limiter.limit("15 per minute", methods=["POST"])
def login():
    """Customer login route accepting either phone number or email."""
    raw_next = request.args.get("next") or request.form.get("next") or ""
    next_url = get_safe_redirect_url(raw_next, default_url=url_for("account.orders"))
    clean_next = next_url if raw_next else ""

    if session.get("user_id"):
        return redirect(next_url)

    brand_name = Setting.get_value("company_name", "Scented Bubbles")

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        if not identifier or not password:
            flash("Please enter your registered phone number or email and password.", "error")
            return render_template("account/login.html", identifier=identifier, brand_name=brand_name, next_url=clean_next)

        # Find user by phone or email
        user = None
        clean_identifier = identifier.lower()
        if re.match(r"^\d{10}$", identifier):
            user = User.query.filter_by(phone=identifier).first()
        if not user:
            user = User.query.filter(User.email.ilike(clean_identifier)).first()
        if not user and identifier.isdigit():
            user = User.query.filter_by(phone=identifier).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account has been deactivated. Please contact customer support.", "error")
                return render_template("account/login.html", identifier=identifier, brand_name=brand_name, next_url=clean_next)

            # Clear previous customer session while keeping any active admin session intact
            clear_customer_session()
            session["user_id"] = user.id
            session["user_name"] = user.name or user.phone or user.email
            session.permanent = True

            flash(f"Welcome back, {session['user_name']}!", "success")
            return redirect(next_url)
        else:
            flash("Invalid phone/email or password. Please check your credentials.", "error")

    return render_template("account/login.html", brand_name=brand_name, next_url=clean_next)


@account_bp.route("/logout")
def logout():
    """Customer sign out."""
    clear_customer_session()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("main.index"))


def get_google_oauth_config():
    """Retrieve Google OAuth credentials from Setting DB with environment variable fallback."""
    enabled_val = Setting.get_value("google_login_enabled", "true")
    is_enabled = str(enabled_val).strip().lower() in ("true", "1", "yes")
    client_id = (Setting.get_value("google_client_id", "") or os.environ.get("GOOGLE_CLIENT_ID", "")).strip()
    client_secret = (Setting.get_value("google_client_secret", "") or os.environ.get("GOOGLE_CLIENT_SECRET", "")).strip()
    return {
        "enabled": is_enabled,
        "client_id": client_id,
        "client_secret": client_secret,
    }


@account_bp.route("/google/login")
def google_login():
    """Initiate Google OAuth 2.0 / OpenID Connect authorization code flow."""
    config = get_google_oauth_config()
    if not config["enabled"]:
        flash("Google Sign-In is currently disabled.", "warning")
        return redirect(url_for("account.login"))

    if not config["client_id"] or not config["client_secret"]:
        flash(
            "Google Sign-In is not configured yet. Store administrators can configure Google Client ID & Secret in Store Settings.",
            "warning",
        )
        return redirect(url_for("account.login"))

    raw_next = request.args.get("next") or ""
    clean_next = get_safe_redirect_url(raw_next, default_url=url_for("account.orders"))

    # Cryptographically secure anti-CSRF state token
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    session["oauth_next"] = clean_next

    # Build redirect URI with HTTPS respect behind proxies
    redirect_uri = url_for("account.google_callback", _external=True)
    if request.headers.get("X-Forwarded-Proto") == "https" and redirect_uri.startswith("http://"):
        redirect_uri = "https://" + redirect_uri[len("http://"):]

    params = {
        "client_id": config["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)


@account_bp.route("/google/callback", methods=["GET", "POST"])
@csrf.exempt
def google_callback():
    """Handle Google OAuth 2.0 callback, exchange code for token, and log customer in."""
    config = get_google_oauth_config()
    if not config["enabled"]:
        flash("Google Sign-In is currently disabled.", "warning")
        return redirect(url_for("account.login"))

    # Check for cancellation or error from Google
    error = request.args.get("error")
    if error:
        if error == "access_denied":
            flash("Google Sign-In was cancelled.", "info")
        else:
            flash(f"Google Sign-In encountered an issue: {error}", "error")
        return redirect(url_for("account.login"))

    # State validation
    state = request.args.get("state")
    expected_state = session.pop("oauth_state", None)
    raw_next = session.pop("oauth_next", None) or url_for("account.orders")
    safe_next = get_safe_redirect_url(raw_next, default_url=url_for("account.orders"))

    if not state or not expected_state or not secrets.compare_digest(state, expected_state):
        flash("Authentication session expired or invalid state. Please try signing in again.", "warning")
        return redirect(url_for("account.login"))

    code = request.args.get("code")
    if not code:
        flash("No authorization code received from Google.", "error")
        return redirect(url_for("account.login"))

    redirect_uri = url_for("account.google_callback", _external=True)
    if request.headers.get("X-Forwarded-Proto") == "https" and redirect_uri.startswith("http://"):
        redirect_uri = "https://" + redirect_uri[len("http://"):]

    try:
        token_payload = {
            "code": code,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        token_resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data=token_payload,
            headers={"Accept": "application/json"},
            timeout=10,
        )
        if not token_resp.ok:
            current_app.logger.error(f"Google OAuth token exchange failed: {token_resp.status_code} {token_resp.text}")
            flash("Unable to verify Google credentials. Please try signing in again.", "error")
            return redirect(url_for("account.login"))

        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            flash("No access token received from Google.", "error")
            return redirect(url_for("account.login"))

        # Fetch user info
        userinfo_resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if not userinfo_resp.ok:
            flash("Failed to retrieve profile details from Google.", "error")
            return redirect(url_for("account.login"))

        userinfo = userinfo_resp.json()
        google_id = str(userinfo.get("sub") or "").strip()
        email = (userinfo.get("email") or "").strip().lower()
        name = (userinfo.get("name") or "").strip()
        avatar = userinfo.get("picture")

        if not google_id or not email:
            flash("Google account did not provide a verified email address.", "error")
            return redirect(url_for("account.login"))

        # Match existing user by google_id or email
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            user = User.query.filter(User.email.ilike(email)).first()
            if user:
                user.google_id = google_id
                if not user.avatar_url and avatar:
                    user.avatar_url = avatar
                if not user.name and name:
                    user.name = name
            else:
                # Create new User
                user = User(
                    email=email,
                    name=name or email.split("@")[0],
                    google_id=google_id,
                    avatar_url=avatar,
                    is_active=True,
                )
                user.set_password(secrets.token_urlsafe(32))
                db.session.add(user)
                db.session.flush()

        if not user.is_active:
            flash("Your account has been deactivated. Please contact customer support.", "error")
            return redirect(url_for("account.login"))

        # Link or create customer record if phone is known or existing customer matches email
        customer = Customer.query.filter_by(user_id=user.id).first()
        if not customer and user.email:
            customer = Customer.query.filter(Customer.email.ilike(user.email)).first()
        if not customer and user.phone:
            customer = Customer.query.filter_by(phone=user.phone).first()

        if customer:
            customer.user_id = user.id
            if not customer.name and user.name:
                customer.name = user.name
            if not customer.email and user.email:
                customer.email = user.email
        elif user.phone:
            customer = Customer(
                phone=user.phone,
                name=user.name,
                email=user.email,
                user_id=user.id,
            )
            db.session.add(customer)

        # Also link any other guest Customer profiles matching this email
        if user.email:
            guest_customers = Customer.query.filter(
                Customer.email.ilike(user.email),
                Customer.user_id.is_(None),
            ).all()
            for gc in guest_customers:
                gc.user_id = user.id

        db.session.commit()

        # Initialize authenticated customer session
        clear_customer_session()
        session["user_id"] = user.id
        session["user_name"] = user.name or user.email
        session.permanent = True

        display_name = user.name or "Shopper"
        flash(f"Welcome, {display_name}! Signed in successfully with Google.", "success")
        return redirect(safe_next)

    except requests.RequestException as re_err:
        current_app.logger.error(f"Google OAuth connection error: {re_err}")
        flash("Could not connect to Google authentication service. Please check your internet connection.", "error")
        return redirect(url_for("account.login"))
    except Exception as e:
        current_app.logger.error(f"Unexpected Google OAuth error: {e}")
        db.session.rollback()
        flash("An unexpected error occurred during Google sign in. Please try again.", "error")
        return redirect(url_for("account.login"))


@account_bp.route("/orders")
@customer_required
def orders():
    """Customer orders overview: Shows ONLY current active in-progress orders.
    Old delivered orders are removed to conserve data and keep dashboard uncluttered.
    """
    user = get_current_user()
    user_orders = user.get_current_orders() if user else []
    brand_name = Setting.get_value("company_name", "Scented Bubbles")

    return render_template(
        "account/orders.html",
        user=user,
        orders=user_orders,
        brand_name=brand_name,
    )


@account_bp.route("/profile", methods=["GET", "POST"])
@customer_required
def profile():
    """Customer profile and default delivery address management."""
    user = get_current_user()
    customer = user.primary_customer
    brand_name = Setting.get_value("company_name", "Scented Bubbles")

    if request.method == "POST":
        action = request.form.get("action", "details")

        if action == "details":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            address_line1 = request.form.get("address_line1", "").strip()
            address_line2 = request.form.get("address_line2", "").strip()
            city = request.form.get("city", "").strip()
            state = request.form.get("state", "").strip()
            pincode = request.form.get("pincode", "").strip()

            if len(name) < 2:
                flash("Please enter a valid full name.", "error")
                return redirect(url_for("account.profile"))

            # Check email uniqueness if changed
            if email and email != (user.email or "").lower():
                existing = User.query.filter_by(email=email).first()
                if existing and existing.id != user.id:
                    flash("This email is already in use by another account.", "error")
                    return redirect(url_for("account.profile"))

            user.name = name
            user.email = email if email else None
            session["user_name"] = name

            if customer:
                customer.name = name
                customer.email = email if email else None
                customer.address_line1 = address_line1
                customer.address_line2 = address_line2 if address_line2 else None
                customer.city = city
                customer.state = state
                customer.pincode = pincode
            else:
                customer = Customer(
                    phone=user.phone or "0000000000",
                    name=name,
                    email=email if email else None,
                    address_line1=address_line1,
                    address_line2=address_line2 if address_line2 else None,
                    city=city,
                    state=state,
                    pincode=pincode,
                    user_id=user.id,
                )
                db.session.add(customer)

            db.session.commit()
            flash("Your profile and shipping details have been updated successfully.", "success")
            return redirect(url_for("account.profile"))

        elif action == "password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            confirm_new_pw = request.form.get("confirm_new_password", "")

            if not user.check_password(current_pw):
                flash("Current password is incorrect.", "error")
                return redirect(url_for("account.profile"))
            if len(new_pw) < 8:
                flash("New password must be at least 8 characters long.", "error")
                return redirect(url_for("account.profile"))
            if new_pw != confirm_new_pw:
                flash("New passwords do not match.", "error")
                return redirect(url_for("account.profile"))

            user.set_password(new_pw)
            db.session.commit()
            flash("Your password has been changed successfully.", "success")
            return redirect(url_for("account.profile"))

    return render_template(
        "account/profile.html",
        user=user,
        customer=customer,
        brand_name=brand_name,
    )


@account_bp.route("/quick-signup", methods=["POST"])
def quick_signup():
    """One-click account creation from post-checkout success page."""
    data = request.get_json(silent=True) or request.form.to_dict()
    phone = str(data.get("phone", "")).strip()
    password = str(data.get("password", "")).strip()
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()

    if not phone or not re.match(r"^[6-9]\d{9}$", phone):
        return jsonify({"success": False, "error": "Invalid phone number."}), 400
    if len(password) < 8:
        return jsonify({"success": False, "error": "Password must be at least 8 characters long."}), 400

    # Check if user already exists with this phone
    existing_user = User.query.filter_by(phone=phone).first()
    if existing_user:
        return jsonify({
            "success": False,
            "error": "An account with this phone number already exists. Please log in.",
            "login_url": url_for("account.login"),
        }), 409

    # Create user
    new_user = User(
        name=name if name else "Valued Customer",
        phone=phone,
        email=email if email else None,
        is_active=True,
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.flush()

    # Link all customer profiles with matching phone
    customers = Customer.query.filter_by(phone=phone).all()
    if customers:
        for c in customers:
            c.user_id = new_user.id
    else:
        customer = Customer(
            phone=phone,
            name=new_user.name,
            email=email if email else None,
            user_id=new_user.id,
        )
        db.session.add(customer)

    db.session.commit()

    # Log in immediately
    clear_customer_session()
    session["user_id"] = new_user.id
    session["user_name"] = new_user.name
    session.permanent = True

    return jsonify({
        "success": True,
        "message": "Account created! You can now track your orders anytime.",
        "redirect_url": url_for("account.orders"),
    })


@account_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute; 20 per hour", methods=["POST"])
def forgot_password():
    """Request a password reset link via registered email or mobile."""
    if session.get("user_id"):
        return redirect(url_for("account.orders"))

    all_s = Setting.get_all_dict()
    brand_name = all_s.get("company_name", "Scented Bubbles")

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        if not identifier:
            flash("Please enter your registered email address or mobile number.", "error")
            return render_template("account/forgot_password.html", brand_name=brand_name)

        user = User.query.filter(
            or_(User.email == identifier.lower(), User.phone == identifier)
        ).first()

        if user and user.is_active:
            s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
            token = s.dumps({"user_id": user.id}, salt="customer-password-reset")
            reset_url = url_for("account.reset_password", token=token, _external=True)

            # Log to server console for development & administrative reference (never shown in UI)
            current_app.logger.info(f"[Password Reset] Link for user {user.id} ({user.email or user.phone}): {reset_url}")

            if user.email:
                sent = NotificationService.send_password_reset_email(user.email, reset_url, brand_name)
                if sent:
                    flash(
                        "Password reset instructions have been dispatched to your registered email address.",
                        "info",
                    )
                else:
                    if current_app.config.get("DEBUG") or current_app.config.get("TESTING"):
                        flash(
                            "SMTP email credentials are not set in .env. We printed the password reset link to your running terminal console (check your command prompt).",
                            "warning",
                        )
                    else:
                        flash(
                            "Unable to send reset email at this moment. Please contact store support on WhatsApp.",
                            "error",
                        )
                return redirect(url_for("account.login"))
            else:
                # Account exists with mobile number only (no linked email)
                import urllib.parse
                support_whatsapp = all_s.get("support_whatsapp") or current_app.config.get("SUPPORT_WHATSAPP", "919876543210")
                wa_msg = urllib.parse.quote(
                    f"Hello {brand_name}, I need help resetting my password for my account with phone number {user.phone}."
                )
                wa_url = f"https://wa.me/{support_whatsapp}?text={wa_msg}"
                return render_template(
                    "account/forgot_password.html",
                    brand_name=brand_name,
                    phone_no_email=True,
                    phone=user.phone,
                    whatsapp_url=wa_url,
                    support_whatsapp=support_whatsapp,
                )

        # Uniform feedback for unknown identifiers to prevent account enumeration
        flash(
            "If an account is associated with that email or phone number, password reset instructions have been dispatched.",
            "info",
        )
        return redirect(url_for("account.login"))

    return render_template("account/forgot_password.html", brand_name=brand_name)


@account_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Set a new password using a verified timed token."""
    if session.get("user_id"):
        return redirect(url_for("account.orders"))

    all_s = Setting.get_all_dict()
    brand_name = all_s.get("company_name", "Scented Bubbles")

    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        data = s.loads(token, salt="customer-password-reset", max_age=3600)  # 1 hour expiration
        user_id = data.get("user_id")
        user = db.session.get(User, user_id)
        if not user or not user.is_active:
            flash("Invalid or deactivated account.", "error")
            return redirect(url_for("account.login"))
    except SignatureExpired:
        flash("The password reset link has expired. Please request a new one.", "error")
        return redirect(url_for("account.forgot_password"))
    except BadSignature:
        flash("Invalid password reset token.", "error")
        return redirect(url_for("account.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("account/reset_password.html", token=token, brand_name=brand_name)

        user.set_password(password)
        db.session.commit()
        flash("Your password has been reset successfully! You can now sign in.", "success")
        return redirect(url_for("account.login"))

    return render_template("account/reset_password.html", token=token, brand_name=brand_name)

