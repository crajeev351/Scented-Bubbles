import datetime
import os
import re
from decimal import Decimal
from functools import wraps
from pathlib import Path
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
    jsonify,
)
from werkzeug.utils import secure_filename
from sqlalchemy import or_, func, desc
from sqlalchemy.orm import selectinload

from app.extensions import db, limiter
from app.models.admins import Admin
from app.models.products import Product
from app.models.product_variants import ProductVariant
from app.models.product_images import ProductImage
from app.models.categories import Category
from app.models.combos import Combo
from app.models.combo_items import ComboItem
from app.models.banners import Banner
from app.models.orders import Order
from app.models.order_items import OrderItem
from app.models.payments import Payment
from app.models.customers import Customer
from app.models.settings import Setting
from app.models.pages import Page
from app.services.cache_service import cache
from app.services.storage import get_storage
from app.services.order_service import (
    update_order_status,
    update_payment_status,
    cancel_order,
    InvalidOrderStateError,
    OrderError,
)
from app.services.whatsapp_service import build_admin_whatsapp_link

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    """Decorator ensuring request has an authenticated admin session and enforces inactivity timeout."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_id"):
            if request.is_json:
                return jsonify({"error": "Unauthorized"}), 401
            flash("Please sign in to access the admin portal.", "error")
            return redirect(url_for("admin.login", next=request.url))

        # Enforce 30-minute admin inactivity timeout
        now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
        last_activity = session.get("admin_last_activity")
        if last_activity and (now_ts - last_activity > 1800):
            session.clear()
            if request.is_json:
                return jsonify({"error": "Admin session expired due to inactivity"}), 401
            flash("Your admin session has expired due to 30 minutes of inactivity. Please sign in again.", "warning")
            return redirect(url_for("admin.login"))
        session["admin_last_activity"] = now_ts

        return f(*args, **kwargs)
    return decorated_function


@admin_bp.context_processor
def inject_admin_globals():
    """Injects live badge counts and brand name into all admin templates."""
    try:
        pending_orders_count = Order.query.filter_by(order_status=Order.STATUS_PENDING).count()
        low_stock_count = ProductVariant.query.filter(
            ProductVariant.stock <= 5,
            ProductVariant.active.is_(True),
            ProductVariant.is_deleted.is_(False),
        ).count()
    except Exception:
        pending_orders_count = 0
        low_stock_count = 0

    brand_name = Setting.get_value("company_name", "Scented Bubbles")
    return {
        "pending_orders_count": pending_orders_count,
        "low_stock_count": low_stock_count,
        "brand_name": brand_name,
    }


def handle_uploaded_file(file_storage, prefix="img", fit_dimensions=None) -> str:
    """Helper to validate by content, enforce 5MB, resize, and compress to WebP (thumb/medium/large).
    If fit_dimensions is specified, automatically crops and fits to target aspect ratio and size.
    """
    if not file_storage or not file_storage.filename:
        return ""
    
    from app.services.image_service import process_and_save_image, ImageError
    try:
        results = process_and_save_image(file_storage, filename=file_storage.filename, prefix=prefix, fit_dimensions=fit_dimensions)
        return results["primary_key"]
    except ImageError as ie:
        raise ValueError(str(ie))


# ==============================================================================
# AUTHENTICATION & SECURITY
# ==============================================================================

@admin_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute; 20 per hour")
def login():
    """Rate-limited admin authentication page with lockout policy and 2FA verification."""
    if session.get("admin_id"):
        return redirect(url_for("admin.dashboard"))

    # Optional secret admin slug check
    secret_slug = Setting.get_value("admin_secret_slug", "").strip()
    if secret_slug and not session.get("admin_secret_verified"):
        key = request.args.get("key", "").strip()
        if key == secret_slug:
            session["admin_secret_verified"] = True
        else:
            return redirect(url_for("main.index"))

    brand_name = Setting.get_value("company_name", "Scented Bubbles")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin = Admin.query.filter_by(username=username, is_active=True).first()
        if admin:
            # Check lockout
            if admin.is_locked():
                mins = admin.minutes_until_unlocked()
                flash(f"This account is temporarily locked due to 5 failed login attempts. Please try again in {mins} minute{'s' if mins > 1 else ''}.", "error")
                return render_template("admin/login.html", brand_name=brand_name)

            if admin.check_password(password):
                admin.record_successful_login()
                db.session.commit()

                # If 2FA enabled, redirect to 2FA verification step
                if admin.is_2fa_enabled and admin.totp_secret:
                    session["admin_2fa_pending_id"] = admin.id
                    session["admin_next_url"] = request.args.get("next")
                    return redirect(url_for("admin.verify_2fa"))

                session.clear()
                session["admin_id"] = admin.id
                session["admin_username"] = admin.username
                session["admin_last_activity"] = datetime.datetime.now(datetime.timezone.utc).timestamp()
                session.permanent = True
                flash("Welcome back to your administration dashboard!", "success")
                next_url = request.args.get("next")
                return redirect(next_url or url_for("admin.dashboard"))
            else:
                admin.record_failed_attempt(max_attempts=5, lockout_minutes=15)
                db.session.commit()
                if admin.is_locked():
                    flash("Account locked for 15 minutes due to 5 consecutive failed attempts.", "error")
                else:
                    attempts_left = max(0, 5 - (admin.failed_login_attempts or 0))
                    flash(f"Invalid credentials. {attempts_left} attempt{'s' if attempts_left != 1 else ''} remaining before temporary lockout.", "error")
        else:
            flash("Invalid credentials or account is disabled.", "error")

    return render_template("admin/login.html", brand_name=brand_name)


@admin_bp.route("/login/verify-2fa", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def verify_2fa():
    """Validates 6-digit TOTP code during two-factor authentication."""
    pending_id = session.get("admin_2fa_pending_id")
    if not pending_id:
        return redirect(url_for("admin.login"))

    admin = db.session.get(Admin, pending_id)
    if not admin or not admin.is_active or not admin.is_2fa_enabled:
        session.pop("admin_2fa_pending_id", None)
        return redirect(url_for("admin.login"))

    brand_name = Setting.get_value("company_name", "Scented Bubbles")

    if request.method == "POST":
        code = request.form.get("totp_code", "").strip()
        from app.services.totp_service import verify_totp
        if verify_totp(admin.totp_secret, code):
            session.clear()
            session["admin_id"] = admin.id
            session["admin_username"] = admin.username
            session["admin_last_activity"] = datetime.datetime.now(datetime.timezone.utc).timestamp()
            session.permanent = True
            flash("Two-factor authentication verified. Welcome back!", "success")
            next_url = session.pop("admin_next_url", None)
            return redirect(next_url or url_for("admin.dashboard"))
        else:
            flash("Invalid 6-digit authentication code. Please check your authenticator app and try again.", "error")

    return render_template("admin/verify_2fa.html", brand_name=brand_name, admin=admin)


@admin_bp.route("/logout")
def logout():
    """Securely terminates admin session."""
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("admin.login"))


# ==============================================================================
# DASHBOARD
# ==============================================================================

@admin_bp.route("/")
@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    """Admin dashboard shell with lightweight aggregation queries and recent orders."""
    today_start = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)

    # Lightweight metric calculations
    today_orders_count = Order.query.filter(Order.created_at >= today_start).count()
    
    today_revenue_res = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= today_start,
        Order.payment_status == Order.PAYMENT_PAID,
    ).scalar() or Decimal("0.00")

    month_revenue_res = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= month_start,
        Order.payment_status == Order.PAYMENT_PAID,
    ).scalar() or Decimal("0.00")

    pending_orders = Order.query.filter_by(order_status=Order.STATUS_PENDING).count()
    pending_payments = Order.query.filter_by(payment_status=Order.PAYMENT_PENDING_VERIFICATION).count()
    total_products = Product.query.filter_by(is_deleted=False).count()
    
    low_stock = ProductVariant.query.filter(
        ProductVariant.stock <= 5,
        ProductVariant.active.is_(True),
        ProductVariant.is_deleted.is_(False),
    ).count()

    recent_orders = (
        Order.query.options(selectinload(Order.customer), selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        today_orders=today_orders_count,
        today_revenue=today_revenue_res,
        month_revenue=month_revenue_res,
        pending_orders=pending_orders,
        pending_payments=pending_payments,
        total_products=total_products,
        low_stock=low_stock,
        recent_orders=recent_orders,
    )


@admin_bp.route("/cache/clear", methods=["POST"])
@admin_required
def clear_cache():
    """Manual cache invalidation action."""
    cache.invalidate_all()
    flash("Storefront cache invalidated successfully! All pages are serving fresh database records.", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))


# ==============================================================================
# SALES ANALYTICS & INVENTORY
# ==============================================================================

@admin_bp.route("/analytics")
@admin_required
def analytics():
    """Sales analytics page with date-range filter and seven Chart.js charts."""
    from app.services import analytics_service
    start_date_str = request.args.get("start_date", "").strip()
    end_date_str = request.args.get("end_date", "").strip()
    date_basis = request.args.get("date_basis", "placed").strip().lower()
    if date_basis not in ("placed", "activity"):
        date_basis = "placed"

    s_date, e_date = None, None
    if start_date_str:
        try:
            s_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if end_date_str:
        try:
            e_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    # Pure SQL aggregated queries only — zero historical order rows in Python
    kpis = analytics_service.get_summary_kpis(s_date, e_date, date_basis=date_basis)
    daily_trend = analytics_service.get_daily_revenue_trend(s_date, e_date, date_basis=date_basis)
    monthly_trend = analytics_service.get_monthly_revenue_trend()
    status_dist = analytics_service.get_orders_by_status(s_date, e_date)
    payment_dist = analytics_service.get_orders_by_payment_status(s_date, e_date)
    bestsellers = analytics_service.get_top_bestsellers(10, s_date, e_date)
    category_sales = analytics_service.get_sales_by_category(s_date, e_date)
    hourly_orders = analytics_service.get_orders_by_hour(s_date, e_date)

    return render_template(
        "admin/analytics.html",
        kpis=kpis,
        daily_trend=daily_trend,
        monthly_trend=monthly_trend,
        status_dist=status_dist,
        payment_dist=payment_dist,
        bestsellers=bestsellers,
        category_sales=category_sales,
        hourly_orders=hourly_orders,
        start_date=start_date_str,
        end_date=end_date_str,
        date_basis=date_basis,
    )


@admin_bp.route("/analytics/data")
@admin_required
def analytics_data():
    """AJAX JSON endpoint returning aggregated chart series only. Zero historical orders loaded into Python."""
    from app.services import analytics_service
    start_date_str = request.args.get("start_date", "").strip()
    end_date_str = request.args.get("end_date", "").strip()
    date_basis = request.args.get("date_basis", "placed").strip().lower()
    if date_basis not in ("placed", "activity"):
        date_basis = "placed"

    s_date, e_date = None, None
    if start_date_str:
        try:
            s_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if end_date_str:
        try:
            e_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    kpis = analytics_service.get_summary_kpis(s_date, e_date, date_basis=date_basis)

    return jsonify({
        "kpis": {
            "total_orders": kpis["total_orders"],
            "valid_orders": kpis["valid_orders"],
            "net_revenue": float(kpis["net_revenue"]),
            "paid_revenue": float(kpis["paid_revenue"]),
            "aov": float(kpis["aov"]),
            "pending_payments_count": kpis.get("pending_payments_count", 0),
            "pending_orders_count": kpis.get("pending_orders_count", 0),
            "shipped_orders_count": kpis.get("shipped_orders_count", 0),
            "delivered_orders_count": kpis.get("delivered_orders_count", 0),
        },
        "daily_trend": analytics_service.get_daily_revenue_trend(s_date, e_date),
        "monthly_trend": analytics_service.get_monthly_revenue_trend(),
        "status_dist": analytics_service.get_orders_by_status(s_date, e_date),
        "payment_dist": analytics_service.get_orders_by_payment_status(s_date, e_date),
        "bestsellers": analytics_service.get_top_bestsellers(10, s_date, e_date),
        "category_sales": analytics_service.get_sales_by_category(s_date, e_date),
        "hourly_orders": analytics_service.get_orders_by_hour(s_date, e_date),
    })


@admin_bp.route("/inventory")
@admin_required
def inventory():
    """Inventory control view with configurable low-stock threshold."""
    default_thresh = int(Setting.get_value("low_stock_threshold", "5") or 5)
    threshold = request.args.get("threshold", default_thresh, type=int)
    filter_type = request.args.get("filter", "all").strip().lower()
    search = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    query = ProductVariant.query.filter_by(is_deleted=False).join(Product).filter(Product.is_deleted == False).options(selectinload(ProductVariant.product))

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                ProductVariant.sku.ilike(pattern),
                ProductVariant.size_label.ilike(pattern),
                Product.name.ilike(pattern),
            )
        )

    if filter_type == "out_of_stock":
        query = query.filter(ProductVariant.stock == 0)
    elif filter_type == "low_stock":
        query = query.filter(ProductVariant.stock > 0, ProductVariant.stock <= threshold)
    elif filter_type == "healthy":
        query = query.filter(ProductVariant.stock > threshold)

    pagination = query.order_by(ProductVariant.stock.asc()).paginate(page=page, per_page=20, error_out=False)

    total_variants = ProductVariant.query.filter_by(is_deleted=False).count()
    out_of_stock_count = ProductVariant.query.filter(ProductVariant.is_deleted == False, ProductVariant.stock == 0).count()
    low_stock_count = ProductVariant.query.filter(ProductVariant.is_deleted == False, ProductVariant.stock > 0, ProductVariant.stock <= threshold).count()

    return render_template(
        "admin/inventory/index.html",
        variants=pagination.items,
        pagination=pagination,
        threshold=threshold,
        filter_type=filter_type,
        search_query=search,
        total_variants=total_variants,
        out_of_stock_count=out_of_stock_count,
        low_stock_count=low_stock_count,
    )


# ==============================================================================
# PRODUCTS & VARIANTS CRUD
# ==============================================================================

@admin_bp.route("/products")
@admin_required
def product_list():
    """Products listing with category filter, search, active filter, and quick update forms."""
    page = request.args.get("page", 1, type=int)
    category_id = request.args.get("category_id", type=int)
    search = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "")

    query = Product.query.filter_by(is_deleted=False).options(
        selectinload(Product.variants),
        selectinload(Product.images),
        selectinload(Product.category),
        selectinload(Product.categories),
    )

    if category_id:
        query = query.filter(
            or_(
                Product.category_id == category_id,
                Product.categories.any(Category.id == category_id),
            )
        )

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Product.name.ilike(pattern),
                Product.slug.ilike(pattern),
                Product.inspired_by.ilike(pattern),
            )
        )

    if status_filter == "active":
        query = query.filter(Product.active.is_(True))
    elif status_filter == "inactive":
        query = query.filter(Product.active.is_(False))

    pagination = query.order_by(Product.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    categories = Category.query.filter_by(is_deleted=False).order_by(Category.name.asc()).all()

    return render_template(
        "admin/products/index.html",
        products=pagination.items,
        pagination=pagination,
        categories=categories,
        selected_category_id=category_id,
        search_query=search,
        status_filter=status_filter,
    )


@admin_bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def product_create():
    """Create a new product with initial variants, primary image, and multiple categories."""
    categories = Category.query.filter_by(is_deleted=False).order_by(Category.display_order.asc(), Category.name.asc()).all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip() or re.sub(r"[^\w\-]", "-", name.lower()).strip("-")
        category_ids = [int(cid) for cid in request.form.getlist("category_ids") if cid.isdigit()]
        if not category_ids and request.form.get("category_id"):
            category_ids = [request.form.get("category_id", type=int)]
        inspired_by = request.form.get("inspired_by", "").strip()
        short_desc = request.form.get("short_description", "").strip()
        full_desc = request.form.get("full_description", "").strip()
        usage = request.form.get("usage_instructions", "").strip()
        is_featured = bool(request.form.get("featured"))
        is_bestseller = bool(request.form.get("bestseller"))
        is_active = bool(request.form.get("active", True))

        if not name or not category_ids:
            flash("Product name and at least one Category are required.", "error")
            return render_template("admin/products/form.html", product=None, categories=categories)

        selected_categories = Category.query.filter(Category.id.in_(category_ids)).all()
        if not selected_categories:
            flash("Please select at least one valid Category.", "error")
            return render_template("admin/products/form.html", product=None, categories=categories)

        if Product.query.filter_by(slug=slug).first():
            flash(f"A product with slug '{slug}' already exists. Please pick a unique slug.", "error")
            return render_template("admin/products/form.html", product=None, categories=categories)

        product = Product(
            category_id=selected_categories[0].id,
            name=name,
            slug=slug,
            inspired_by=inspired_by,
            fragrance_family=None,
            short_description=short_desc,
            full_description=full_desc,
            top_notes=None,
            heart_notes=None,
            base_notes=None,
            usage_instructions=usage,
            featured=is_featured,
            bestseller=is_bestseller,
            active=is_active,
        )
        product.categories = selected_categories
        db.session.add(product)
        db.session.flush()

        # Handle Image
        uploaded_img = request.files.get("primary_image")
        image_key = request.form.get("image_key", "").strip()
        if uploaded_img and uploaded_img.filename:
            try:
                image_key = handle_uploaded_file(uploaded_img, prefix="prod")
            except ValueError as ve:
                flash(str(ve), "error")
        if not image_key:
            image_key = "/static/images/placeholder_perfume.webp"

        img_obj = ProductImage(
            product_id=product.id,
            image_key=image_key,
            alt_text=f"{product.name} bottle",
            is_primary=True,
            display_order=0,
        )
        db.session.add(img_obj)

        # Parse variants
        labels = request.form.getlist("variant_label[]")
        skus = request.form.getlist("variant_sku[]")
        prices = request.form.getlist("variant_price[]")
        disc_prices = request.form.getlist("variant_discounted_price[]")
        stocks = request.form.getlist("variant_stock[]")

        for i in range(len(labels)):
            lbl = labels[i].strip()
            sku = skus[i].strip() if i < len(skus) else ""
            if not lbl:
                continue
            if not sku:
                sku = f"{product.slug[:4].upper()}-{lbl[:4].upper()}-{i+1}"
            
            # Check unique SKU
            if ProductVariant.query.filter_by(sku=sku).first():
                sku = f"{sku}-{datetime.datetime.now().strftime('%M%S')}"

            p = Decimal(prices[i]) if i < len(prices) and prices[i] else Decimal("999.00")
            dp = Decimal(disc_prices[i]) if i < len(disc_prices) and disc_prices[i] else None
            stk = int(stocks[i]) if i < len(stocks) and stocks[i] else 0

            var = ProductVariant(
                product_id=product.id,
                size_label=lbl,
                sku=sku,
                price=p,
                discounted_price=dp,
                stock=stk,
                active=True,
                display_order=i,
            )
            db.session.add(var)

        db.session.commit()
        cache.invalidate_all()
        flash(f"Product '{product.name}' created successfully with variants!", "success")
        return redirect(url_for("admin.product_list"))

    return render_template("admin/products/form.html", product=None, categories=categories)


@admin_bp.route("/products/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(id):
    """Edit product details, manage variants, upload additional images."""
    product = Product.query.get_or_404(id)
    categories = Category.query.filter_by(is_deleted=False).order_by(Category.display_order.asc(), Category.name.asc()).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip()
        category_ids = [int(cid) for cid in request.form.getlist("category_ids") if cid.isdigit()]
        if not category_ids and request.form.get("category_id"):
            category_ids = [request.form.get("category_id", type=int)]

        if not name or not category_ids:
            flash("Product name and at least one Category are required.", "error")
            return render_template("admin/products/form.html", product=product, categories=categories)

        selected_categories = Category.query.filter(Category.id.in_(category_ids)).all()
        if not selected_categories:
            flash("Please select at least one valid Category.", "error")
            return render_template("admin/products/form.html", product=product, categories=categories)

        # Check slug conflict with other products
        existing = Product.query.filter(Product.slug == slug, Product.id != product.id).first()
        if existing:
            flash(f"Slug '{slug}' is already in use by another product.", "error")
            return render_template("admin/products/form.html", product=product, categories=categories)

        product.name = name
        product.slug = slug
        product.categories = selected_categories
        inspired_by = request.form.get("inspired_by", "").strip()
        product.inspired_by = inspired_by
        product.fragrance_family = None
        product.short_description = request.form.get("short_description", "").strip()
        product.full_description = request.form.get("full_description", "").strip()
        product.top_notes = None
        product.heart_notes = None
        product.base_notes = None
        product.usage_instructions = request.form.get("usage_instructions", "").strip()
        product.featured = bool(request.form.get("featured"))
        product.bestseller = bool(request.form.get("bestseller"))
        product.active = bool(request.form.get("active"))

        # Update existing variants
        for var in product.variants:
            v_id_str = str(var.id)
            if f"var_label_{v_id_str}" in request.form:
                var.size_label = request.form.get(f"var_label_{v_id_str}", var.size_label).strip()
                var.sku = request.form.get(f"var_sku_{v_id_str}", var.sku).strip()
                p_val = request.form.get(f"var_price_{v_id_str}", "").strip()
                if p_val:
                    var.price = Decimal(p_val)
                dp_val = request.form.get(f"var_discounted_price_{v_id_str}", "").strip()
                var.discounted_price = Decimal(dp_val) if dp_val else None
                s_val = request.form.get(f"var_stock_{v_id_str}", "").strip()
                if s_val:
                    var.stock = int(s_val)
                var.active = bool(request.form.get(f"var_active_{v_id_str}"))

        # Handle newly added variant row if filled
        new_label = request.form.get("new_variant_label", "").strip()
        if new_label:
            new_sku = request.form.get("new_variant_sku", "").strip() or f"{product.slug[:4].upper()}-{new_label[:4].upper()}"
            new_price = Decimal(request.form.get("new_variant_price", "999.00"))
            new_dp = Decimal(request.form.get("new_variant_discounted_price", "")) if request.form.get("new_variant_discounted_price") else None
            new_stock = int(request.form.get("new_variant_stock", 0))

            if ProductVariant.query.filter_by(sku=new_sku).first():
                new_sku = f"{new_sku}-{datetime.datetime.now().strftime('%M%S')}"

            new_v = ProductVariant(
                product_id=product.id,
                size_label=new_label,
                sku=new_sku,
                price=new_price,
                discounted_price=new_dp,
                stock=new_stock,
                active=True,
                display_order=len(product.variants),
            )
            db.session.add(new_v)

        # Upload additional image
        add_img = request.files.get("additional_image")
        if add_img and add_img.filename:
            try:
                new_img_key = handle_uploaded_file(add_img, prefix="prod")
                img_record = ProductImage(
                    product_id=product.id,
                    image_key=new_img_key,
                    alt_text=f"{product.name} image",
                    is_primary=False,
                    display_order=len(product.images),
                )
                db.session.add(img_record)
            except ValueError as ve:
                flash(str(ve), "error")

        db.session.commit()
        cache.invalidate_all()
        flash(f"Product '{product.name}' updated successfully!", "success")
        return redirect(url_for("admin.product_list"))

    return render_template("admin/products/form.html", product=product, categories=categories)


@admin_bp.route("/products/<int:id>/toggle", methods=["POST"])
@admin_required
def product_toggle(id):
    """Enable or disable product visibility."""
    product = Product.query.get_or_404(id)
    product.active = not product.active
    db.session.commit()
    cache.invalidate_all()
    flash(f"Product '{product.name}' {'activated' if product.active else 'deactivated'}.", "info")
    return redirect(request.referrer or url_for("admin.product_list"))


@admin_bp.route("/products/<int:id>/delete", methods=["POST"])
@admin_required
def product_delete(id):
    """Soft delete product and its variants."""
    product = Product.query.get_or_404(id)
    product.is_deleted = True
    product.active = False
    for v in product.variants:
        v.is_deleted = True
        v.active = False
    db.session.commit()
    cache.invalidate_all()
    flash(f"Product '{product.name}' was archived.", "success")
    return redirect(url_for("admin.product_list"))


@admin_bp.route("/products/variants/<int:id>/quick-update", methods=["POST"])
@admin_required
def variant_quick_update(id):
    """Instant inline update for variant price, discounted price, and stock."""
    variant = db.session.get(ProductVariant, id)
    if not variant:
        flash("Variant not found", "error")
        return redirect(url_for("admin.product_list"))

    price_val = request.form.get("price", "").strip()
    disc_val = request.form.get("discounted_price", "").strip()
    stock_val = request.form.get("stock", "").strip()

    try:
        if price_val:
            variant.price = Decimal(price_val)
        variant.discounted_price = Decimal(disc_val) if disc_val else None
        if stock_val != "":
            variant.stock = max(0, int(stock_val))

        db.session.commit()
        cache.invalidate_all()
        flash(f"Quick update saved for {variant.product.name} ({variant.size_label})!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Update failed: {e}", "error")

    return redirect(request.referrer or url_for("admin.product_list"))


# ==============================================================================
# CATEGORIES CRUD
# ==============================================================================

@admin_bp.route("/categories")
@admin_required
def category_list():
    """List categories with product counts and archive support."""
    status_filter = request.args.get("status", "all").strip().lower()

    base_query = Category.query
    if status_filter == "active":
        query = base_query.filter_by(is_deleted=False, active=True)
    elif status_filter == "inactive":
        query = base_query.filter_by(is_deleted=False, active=False)
    elif status_filter == "archived":
        query = base_query.filter_by(is_deleted=True)
    else:
        status_filter = "all"
        query = base_query

    categories = (
        query.order_by(Category.is_deleted.asc(), Category.display_order.asc(), Category.name.asc())
        .all()
    )

    total_count = Category.query.count()
    active_count = Category.query.filter_by(is_deleted=False, active=True).count()
    archived_count = Category.query.filter_by(is_deleted=True).count()

    return render_template(
        "admin/categories/index.html",
        categories=categories,
        status_filter=status_filter,
        total_count=total_count,
        active_count=active_count,
        archived_count=archived_count,
    )


@admin_bp.route("/categories/new", methods=["GET", "POST"])
@admin_required
def category_create():
    """Add a new category."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip() or re.sub(r"[^\w\-]", "-", name.lower()).strip("-")
        desc = request.form.get("description", "").strip()
        display_order = request.form.get("display_order", 0, type=int)
        active = bool(request.form.get("active", True))

        if not name:
            flash("Category name is required.", "error")
            return render_template("admin/categories/form.html", category=None)

        existing = Category.query.filter_by(slug=slug).first()
        if existing:
            if existing.is_deleted:
                flash(
                    f"Category '{existing.name}' with slug '{slug}' already exists in archives. "
                    "You can unarchive it from the categories list or delete it permanently first.",
                    "warning",
                )
            else:
                flash(f"Category slug '{slug}' already exists.", "error")
            return render_template("admin/categories/form.html", category=None)

        cat = Category(
            name=name,
            slug=slug,
            description=desc,
            display_order=display_order,
            active=active,
            is_deleted=False,
        )

        img_file = request.files.get("image")
        if img_file and img_file.filename:
            try:
                cat.image_url = handle_uploaded_file(img_file, prefix="cat", fit_dimensions=(800, 450))
            except ValueError as ve:
                flash(str(ve), "error")

        db.session.add(cat)
        db.session.commit()
        cache.invalidate_all()
        flash(f"Category '{cat.name}' created successfully!", "success")
        return redirect(url_for("admin.category_list"))

    return render_template("admin/categories/form.html", category=None)


@admin_bp.route("/categories/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def category_edit(id):
    """Edit existing category."""
    category = Category.query.get_or_404(id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip() or re.sub(r"[^\w\-]", "-", name.lower()).strip("-")
        desc = request.form.get("description", "").strip()
        display_order = request.form.get("display_order", 0, type=int)
        active = bool(request.form.get("active"))

        if not name:
            flash("Category name is required.", "error")
            return render_template("admin/categories/form.html", category=category)

        existing = Category.query.filter(Category.slug == slug, Category.id != category.id).first()
        if existing:
            flash(f"Category slug '{slug}' is already taken.", "error")
            return render_template("admin/categories/form.html", category=category)

        category.name = name
        category.slug = slug
        category.description = desc
        category.display_order = display_order
        category.active = active

        if request.form.get("remove_image"):
            category.image_url = None

        img_file = request.files.get("image")
        if img_file and img_file.filename:
            try:
                category.image_url = handle_uploaded_file(img_file, prefix="cat", fit_dimensions=(800, 450))
            except ValueError as ve:
                flash(str(ve), "error")

        # If user marked an archived category as active during edit, unarchive it
        if active and category.is_deleted:
            category.is_deleted = False

        db.session.commit()
        cache.invalidate_all()
        flash(f"Category '{category.name}' updated successfully!", "success")
        return redirect(url_for("admin.category_list"))

    return render_template("admin/categories/form.html", category=category)


@admin_bp.route("/categories/<int:id>/toggle", methods=["POST"])
@admin_required
def category_toggle(id):
    """Toggle category active state."""
    category = Category.query.get_or_404(id)
    if category.is_deleted:
        category.is_deleted = False
        category.active = True
        flash(f"Category '{category.name}' unarchived and activated.", "info")
    else:
        category.active = not category.active
        flash(f"Category '{category.name}' {'activated' if category.active else 'deactivated'}.", "info")
    db.session.commit()
    cache.invalidate_all()
    return redirect(url_for("admin.category_list"))


@admin_bp.route("/categories/<int:id>/archive", methods=["POST"])
@admin_required
def category_archive(id):
    """Archive (soft delete) category."""
    category = Category.query.get_or_404(id)
    category.is_deleted = True
    category.active = False
    db.session.commit()
    cache.invalidate_all()
    flash(f"Category '{category.name}' archived.", "success")
    return redirect(url_for("admin.category_list"))


@admin_bp.route("/categories/<int:id>/unarchive", methods=["POST"])
@admin_required
def category_unarchive(id):
    """Restore an archived category."""
    category = Category.query.get_or_404(id)
    category.is_deleted = False
    category.active = True
    db.session.commit()
    cache.invalidate_all()
    flash(f"Category '{category.name}' unarchived and restored.", "success")
    return redirect(url_for("admin.category_list"))


@admin_bp.route("/categories/<int:id>/delete", methods=["POST"])
@admin_bp.route("/categories/<int:id>/permanent-delete", methods=["POST"])
@admin_required
def category_delete(id):
    """Permanently delete category from database if no products are assigned."""
    category = Category.query.get_or_404(id)
    product_count = category.products.count()
    if product_count > 0:
        flash(
            f"Cannot delete category '{category.name}' because {product_count} product(s) are assigned to it. "
            "Please reassign or delete those products first, or keep it archived.",
            "error",
        )
        return redirect(url_for("admin.category_list"))

    cat_name = category.name
    db.session.delete(category)
    db.session.commit()
    cache.invalidate_all()
    flash(f"Category '{cat_name}' permanently deleted.", "success")
    return redirect(url_for("admin.category_list"))


# ==============================================================================
# COMBOS CRUD
# ==============================================================================

@admin_bp.route("/combos")
@admin_required
def combo_list():
    """List all combos with items, pricing, and stock status."""
    combos = Combo.query.filter_by(is_deleted=False).order_by(Combo.display_order.asc()).all()
    return render_template("admin/combos/index.html", combos=combos)


@admin_bp.route("/combos/new", methods=["GET", "POST"])
@admin_required
def combo_create():
    """Create a new combo with variant component items."""
    variants = ProductVariant.query.filter_by(active=True, is_deleted=False).all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip() or re.sub(r"[^\w\-]", "-", name.lower()).strip("-")
        short_desc = request.form.get("short_description", "").strip()
        full_desc = request.form.get("full_description", "").strip()
        price = Decimal(request.form.get("combo_price", "0.00"))
        display_order = request.form.get("display_order", 0, type=int)
        active = bool(request.form.get("active", True))

        if not name or price <= 0:
            flash("Combo name and a positive price are required.", "error")
            return render_template("admin/combos/form.html", combo=None, variants=variants)

        # Image upload
        img_file = request.files.get("image")
        image_key = "/static/images/placeholder_combo.webp"
        if img_file and img_file.filename:
            try:
                image_key = handle_uploaded_file(img_file, prefix="combo")
            except ValueError as ve:
                flash(str(ve), "error")

        combo = Combo(
            name=name,
            slug=slug,
            short_description=short_desc,
            full_description=full_desc,
            combo_price=price,
            image_key=image_key,
            display_order=display_order,
            active=active,
        )
        db.session.add(combo)
        db.session.flush()

        # Component variant lines (supports multiple products & aggregates duplicates)
        selected_variants = request.form.getlist("variant_id[]")
        quantities = request.form.getlist("quantity[]")
        item_qty_map = {}

        for idx, vid_str in enumerate(selected_variants):
            if vid_str and vid_str.strip():
                try:
                    vid = int(vid_str)
                    qty = int(quantities[idx]) if idx < len(quantities) and quantities[idx] else 1
                    qty = max(1, qty)
                    item_qty_map[vid] = item_qty_map.get(vid, 0) + qty
                except (ValueError, TypeError):
                    continue

        for vid, qty in item_qty_map.items():
            citem = ComboItem(combo_id=combo.id, product_variant_id=vid, quantity=qty)
            db.session.add(citem)

        db.session.commit()
        cache.invalidate_all()
        flash(f"Combo '{combo.name}' created successfully!", "success")
        return redirect(url_for("admin.combo_list"))

    return render_template("admin/combos/form.html", combo=None, variants=variants)


@admin_bp.route("/combos/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def combo_edit(id):
    """Edit combo details and components."""
    combo = Combo.query.get_or_404(id)
    variants = ProductVariant.query.filter_by(active=True, is_deleted=False).all()

    if request.method == "POST":
        combo.name = request.form.get("name", "").strip()
        combo.slug = request.form.get("slug", "").strip()
        combo.short_description = request.form.get("short_description", "").strip()
        combo.full_description = request.form.get("full_description", "").strip()
        combo.combo_price = Decimal(request.form.get("combo_price", "0.00"))
        combo.display_order = request.form.get("display_order", 0, type=int)
        combo.active = bool(request.form.get("active"))

        img_file = request.files.get("image")
        if img_file and img_file.filename:
            try:
                combo.image_key = handle_uploaded_file(img_file, prefix="combo")
            except ValueError as ve:
                flash(str(ve), "error")

        # Refresh combo items (supports multiple products & aggregates duplicates)
        ComboItem.query.filter_by(combo_id=combo.id).delete()
        selected_variants = request.form.getlist("variant_id[]")
        quantities = request.form.getlist("quantity[]")
        item_qty_map = {}

        for idx, vid_str in enumerate(selected_variants):
            if vid_str and vid_str.strip():
                try:
                    vid = int(vid_str)
                    qty = int(quantities[idx]) if idx < len(quantities) and quantities[idx] else 1
                    qty = max(1, qty)
                    item_qty_map[vid] = item_qty_map.get(vid, 0) + qty
                except (ValueError, TypeError):
                    continue

        for vid, qty in item_qty_map.items():
            citem = ComboItem(combo_id=combo.id, product_variant_id=vid, quantity=qty)
            db.session.add(citem)

        db.session.commit()
        cache.invalidate_all()
        flash(f"Combo '{combo.name}' updated successfully!", "success")
        return redirect(url_for("admin.combo_list"))

    return render_template("admin/combos/form.html", combo=combo, variants=variants)


@admin_bp.route("/combos/<int:id>/toggle", methods=["POST"])
@admin_required
def combo_toggle(id):
    combo = Combo.query.get_or_404(id)
    combo.active = not combo.active
    db.session.commit()
    cache.invalidate_all()
    flash(f"Combo '{combo.name}' {'activated' if combo.active else 'deactivated'}.", "info")
    return redirect(url_for("admin.combo_list"))


@admin_bp.route("/combos/<int:id>/delete", methods=["POST"])
@admin_required
def combo_delete(id):
    combo = Combo.query.get_or_404(id)
    combo.is_deleted = True
    combo.active = False
    db.session.commit()
    cache.invalidate_all()
    flash(f"Combo '{combo.name}' archived.", "success")
    return redirect(url_for("admin.combo_list"))


# ==============================================================================
# BANNERS CRUD
# ==============================================================================

@admin_bp.route("/banners")
@admin_required
def banner_list():
    banners = Banner.query.filter_by(is_deleted=False).order_by(Banner.display_order.asc(), Banner.id.asc()).all()
    return render_template("admin/banners/index.html", banners=banners)


@admin_bp.route("/banners/new", methods=["GET", "POST"])
@admin_required
def banner_create():
    products = Product.query.filter_by(is_deleted=False).order_by(Product.name.asc()).all()
    combos = Combo.query.filter_by(is_deleted=False).order_by(Combo.name.asc()).all()
    categories = Category.query.filter_by(is_deleted=False).order_by(Category.name.asc()).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subtitle = request.form.get("subtitle", "").strip()
        tagline = request.form.get("tagline", "").strip()
        button_text = request.form.get("button_text", "SHOP NOW").strip() or "SHOP NOW"
        secondary_button_text = request.form.get("secondary_button_text", "").strip()
        secondary_button_link = request.form.get("secondary_button_link", "").strip()
        target_type = request.form.get("target_type", "custom").strip()
        target_id = None
        link_url = request.form.get("link_url", "/products").strip()
        display_order = request.form.get("display_order", 0, type=int)
        overlay_opacity = max(10, min(95, request.form.get("overlay_opacity", 55, type=int)))
        active = bool(request.form.get("active", True))

        if target_type == "product":
            pid = request.form.get("product_id", type=int)
            if pid:
                target_id = pid
                prod = db.session.get(Product, pid)
                if prod:
                    link_url = f"/products/{prod.slug}"
        elif target_type == "combo":
            cid = request.form.get("combo_id", type=int)
            if cid:
                target_id = cid
                cmb = db.session.get(Combo, cid)
                if cmb:
                    link_url = f"/combos/{cmb.slug}"
        elif target_type == "category":
            catid = request.form.get("category_id", type=int)
            if catid:
                target_id = catid
                cat = db.session.get(Category, catid)
                if cat:
                    link_url = f"/categories/{cat.slug}"
        else:
            target_type = "custom"
            target_id = None

        if not title:
            flash("Banner headline title is required.", "error")
            return render_template(
                "admin/banners/form.html",
                banner=None,
                products=products,
                combos=combos,
                categories=categories,
            )

        img_file = request.files.get("image")
        image_key = "/static/images/placeholder_banner.webp"
        if img_file and img_file.filename:
            try:
                image_key = handle_uploaded_file(img_file, prefix="banner", fit_dimensions=(1920, 600))
            except ValueError as ve:
                flash(str(ve), "error")

        img_mobile_file = request.files.get("image_mobile")
        image_mobile_key = None
        if img_mobile_file and img_mobile_file.filename:
            try:
                image_mobile_key = handle_uploaded_file(img_mobile_file, prefix="banner_mob", fit_dimensions=(800, 800))
            except ValueError as ve:
                flash(str(ve), "error")

        banner = Banner(
            title=title,
            subtitle=subtitle,
            tagline=tagline,
            button_text=button_text,
            secondary_button_text=secondary_button_text,
            secondary_button_link=secondary_button_link,
            target_type=target_type,
            target_id=target_id,
            overlay_opacity=overlay_opacity,
            link_url=link_url,
            image_key=image_key,
            image_mobile_key=image_mobile_key,
            display_order=display_order,
            active=active,
        )
        db.session.add(banner)
        db.session.commit()
        cache.invalidate_all()
        flash("Promotional hero banner created successfully!", "success")
        return redirect(url_for("admin.banner_list"))

    return render_template(
        "admin/banners/form.html",
        banner=None,
        products=products,
        combos=combos,
        categories=categories,
    )


@admin_bp.route("/banners/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def banner_edit(id):
    banner = Banner.query.get_or_404(id)
    products = Product.query.filter_by(is_deleted=False).order_by(Product.name.asc()).all()
    combos = Combo.query.filter_by(is_deleted=False).order_by(Combo.name.asc()).all()
    categories = Category.query.filter_by(is_deleted=False).order_by(Category.name.asc()).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subtitle = request.form.get("subtitle", "").strip()
        tagline = request.form.get("tagline", "").strip()
        button_text = request.form.get("button_text", "SHOP NOW").strip() or "SHOP NOW"
        secondary_button_text = request.form.get("secondary_button_text", "").strip()
        secondary_button_link = request.form.get("secondary_button_link", "").strip()
        target_type = request.form.get("target_type", "custom").strip()
        target_id = None
        link_url = request.form.get("link_url", "/products").strip()
        display_order = request.form.get("display_order", 0, type=int)
        overlay_opacity = max(10, min(95, request.form.get("overlay_opacity", 55, type=int)))
        active = bool(request.form.get("active"))

        if not title:
            flash("Banner headline title is required.", "error")
            return render_template(
                "admin/banners/form.html",
                banner=banner,
                products=products,
                combos=combos,
                categories=categories,
            )

        if target_type == "product":
            pid = request.form.get("product_id", type=int)
            if pid:
                target_id = pid
                prod = db.session.get(Product, pid)
                if prod:
                    link_url = f"/products/{prod.slug}"
        elif target_type == "combo":
            cid = request.form.get("combo_id", type=int)
            if cid:
                target_id = cid
                cmb = db.session.get(Combo, cid)
                if cmb:
                    link_url = f"/combos/{cmb.slug}"
        elif target_type == "category":
            catid = request.form.get("category_id", type=int)
            if catid:
                target_id = catid
                cat = db.session.get(Category, catid)
                if cat:
                    link_url = f"/categories/{cat.slug}"
        else:
            target_type = "custom"
            target_id = None

        banner.title = title
        banner.subtitle = subtitle
        banner.tagline = tagline
        banner.button_text = button_text
        banner.secondary_button_text = secondary_button_text
        banner.secondary_button_link = secondary_button_link
        banner.target_type = target_type
        banner.target_id = target_id
        banner.overlay_opacity = overlay_opacity
        banner.link_url = link_url
        banner.display_order = display_order
        banner.active = active

        # Desktop banner image upload
        img_file = request.files.get("image")
        if img_file and img_file.filename:
            try:
                banner.image_key = handle_uploaded_file(img_file, prefix="banner", fit_dimensions=(1920, 600))
            except ValueError as ve:
                flash(str(ve), "error")

        # Option to remove mobile-specific image (revert to desktop auto-fit)
        if request.form.get("remove_mobile_image") == "1":
            banner.image_mobile_key = None

        # Mobile banner image upload
        img_mobile_file = request.files.get("image_mobile")
        if img_mobile_file and img_mobile_file.filename:
            try:
                banner.image_mobile_key = handle_uploaded_file(img_mobile_file, prefix="banner_mob", fit_dimensions=(800, 800))
            except ValueError as ve:
                flash(str(ve), "error")

        db.session.commit()
        cache.invalidate_all()
        flash("Promotional hero banner updated successfully!", "success")
        return redirect(url_for("admin.banner_list"))

    return render_template(
        "admin/banners/form.html",
        banner=banner,
        products=products,
        combos=combos,
        categories=categories,
    )


@admin_bp.route("/banners/<int:id>/toggle", methods=["POST"])
@admin_required
def banner_toggle(id):
    banner = Banner.query.get_or_404(id)
    banner.active = not banner.active
    db.session.commit()
    cache.invalidate_all()
    flash(f"Banner {'activated' if banner.active else 'deactivated'}.", "info")
    return redirect(url_for("admin.banner_list"))


@admin_bp.route("/banners/<int:id>/delete", methods=["POST"])
@admin_required
def banner_delete(id):
    banner = Banner.query.get_or_404(id)
    banner.is_deleted = True
    banner.active = False
    db.session.commit()
    cache.invalidate_all()
    flash("Banner removed from slider.", "success")
    return redirect(url_for("admin.banner_list"))


# ==============================================================================
# ORDER MANAGEMENT
# ==============================================================================

@admin_bp.route("/orders")
@admin_required
def order_list():
    """Order management with search and filters by status, payment, and date."""
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    order_status = request.args.get("order_status", "").strip()
    payment_status = request.args.get("payment_status", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    query = Order.query.options(selectinload(Order.customer), selectinload(Order.items), selectinload(Order.payments))

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Order.order_id.ilike(search_pattern),
                Order.shipping_phone.ilike(search_pattern),
                Order.shipping_name.ilike(search_pattern),
            )
        )

    if order_status:
        query = query.filter(Order.order_status == order_status.upper())

    if payment_status:
        query = query.filter(Order.payment_status == payment_status.upper())

    if start_date:
        try:
            s_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Order.created_at >= s_dt)
        except ValueError:
            pass

    if end_date:
        try:
            e_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(Order.created_at <= e_dt)
        except ValueError:
            pass

    pagination = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=15, error_out=False)

    return render_template(
        "admin/orders/index.html",
        orders=pagination.items,
        pagination=pagination,
        search_query=search,
        selected_order_status=order_status,
        selected_payment_status=payment_status,
        start_date=start_date,
        end_date=end_date,
        order_statuses=Order.ORDER_STATUSES,
        payment_statuses=Order.PAYMENT_STATUSES,
    )


@admin_bp.route("/orders/<order_id>")
@admin_required
def order_detail(order_id):
    """Detailed view for single order with status transition actions and WhatsApp link."""
    order = (
        Order.query.filter_by(order_id=order_id)
        .options(selectinload(Order.customer), selectinload(Order.items), selectinload(Order.payments))
        .first_or_404()
    )

    brand_name = Setting.get_value("company_name", "Scented Bubbles")
    admin_wa_link = build_admin_whatsapp_link(order, brand_name=brand_name)

    # Allowed next order status transitions
    transitions_map = {
        Order.STATUS_PENDING: [Order.STATUS_CONFIRMED, Order.STATUS_CANCELLED],
        Order.STATUS_CONFIRMED: [Order.STATUS_PACKED, Order.STATUS_CANCELLED],
        Order.STATUS_PACKED: [Order.STATUS_SHIPPED],
        Order.STATUS_SHIPPED: [Order.STATUS_DELIVERED],
        Order.STATUS_DELIVERED: [],
        Order.STATUS_CANCELLED: [],
    }
    allowed_transitions = transitions_map.get(order.order_status, [])

    return render_template(
        "admin/orders/detail.html",
        order=order,
        admin_wa_link=admin_wa_link,
        allowed_transitions=allowed_transitions,
    )


@admin_bp.route("/orders/<order_id>/status", methods=["POST"])
@admin_required
def order_update_status(order_id):
    """Enforces valid status transitions in the service layer with shipping tracking support."""
    new_status = request.form.get("status", "").strip().upper()
    courier_name = request.form.get("courier_name", "").strip() or None
    tracking_number = request.form.get("tracking_number", "").strip() or None
    tracking_url = request.form.get("tracking_url", "").strip() or None
    notes = request.form.get("notes", "").strip() or None

    try:
        order = update_order_status(
            order_id,
            new_status,
            courier_name=courier_name,
            tracking_number=tracking_number,
            tracking_url=tracking_url,
            notes=notes,
            operator="Store Admin",
        )
        flash(f"Order #{order.order_id} status updated to {order.order_status}.", "success")
    except InvalidOrderStateError as ise:
        flash(str(ise), "error")
    except OrderError as oe:
        flash(str(oe), "error")
    except Exception as e:
        flash(f"Unexpected error updating order status: {e}", "error")

    return redirect(url_for("admin.order_detail", order_id=order_id))


@admin_bp.route("/orders/<order_id>/verify-payment", methods=["POST"])
@admin_required
def order_verify_payment(order_id):
    """Admin verifies manual UPI or COD payment receipt."""
    admin_notes = request.form.get("admin_notes", "Verified by Store Admin").strip()
    try:
        order = update_payment_status(order_id, Order.PAYMENT_PAID, admin_notes=admin_notes)
        flash(f"Payment for order #{order.order_id} verified as PAID!", "success")
    except Exception as e:
        flash(f"Failed to verify payment: {e}", "error")

    return redirect(url_for("admin.order_detail", order_id=order_id))


@admin_bp.route("/orders/<order_id>/reject-payment", methods=["POST"])
@admin_required
def order_reject_payment(order_id):
    """Admin rejects invalid/unreceived payment: sets status FAILED, cancels order, and restores stock!"""
    reason = request.form.get("reason", "Bank reference / UTR could not be verified").strip()
    try:
        # update_payment_status automatically restores reserved stock on FAILED
        order = update_payment_status(order_id, Order.PAYMENT_FAILED, admin_notes=reason)
        flash(f"Payment rejected for order #{order.order_id}. Reserved stock restored and order cancelled.", "warning")
    except Exception as e:
        flash(f"Failed to reject payment: {e}", "error")

    return redirect(url_for("admin.order_detail", order_id=order_id))


@admin_bp.route("/orders/<order_id>/cancel", methods=["POST"])
@admin_required
def order_cancel(order_id):
    """Manually cancel order and restore stock."""
    reason = request.form.get("reason", "Cancelled by Admin").strip()
    try:
        order = cancel_order(order_id, reason=reason)
        flash(f"Order #{order.order_id} cancelled and stock successfully restored to catalog.", "warning")
    except Exception as e:
        flash(f"Failed to cancel order: {e}", "error")

    return redirect(url_for("admin.order_detail", order_id=order_id))


@admin_bp.route("/orders/<order_id>/delete", methods=["POST"])
@admin_required
def order_delete(order_id):
    """Permanently delete an order and its cascading items, payments, and history to free up database storage."""
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    oid = order.order_id
    try:
        db.session.delete(order)
        db.session.commit()
        flash(f"Order #{oid} and all associated records have been permanently deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to delete order #{oid}: {e}", "error")
        return redirect(url_for("admin.order_detail", order_id=oid))

    return redirect(url_for("admin.order_list"))


@admin_bp.route("/orders/purge-delivered", methods=["POST"])
@admin_required
def order_purge_delivered():
    """Bulk purge all delivered orders to permanently free up server database storage."""
    try:
        delivered_orders = Order.query.filter_by(order_status=Order.STATUS_DELIVERED).all()
        count = len(delivered_orders)
        for o in delivered_orders:
            db.session.delete(o)
        db.session.commit()
        flash(f"Successfully purged {count} delivered order(s) from database.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to purge delivered orders: {e}", "error")

    return redirect(url_for("admin.order_list"))


# ==============================================================================
# CUSTOMERS LIST
# ==============================================================================

@admin_bp.route("/customers")
@admin_required
def customer_list():
    """List customer records with order count and total spend."""
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()

    query = Customer.query
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Customer.phone.ilike(pattern),
                Customer.name.ilike(pattern),
                Customer.email.ilike(pattern),
            )
        )

    pagination = query.order_by(Customer.created_at.desc()).paginate(page=page, per_page=20, error_out=False)

    return render_template("admin/customers/index.html", customers=pagination.items, pagination=pagination, search_query=search)


# ==============================================================================
# POLICY PAGES EDIT
# ==============================================================================

@admin_bp.route("/pages")
@admin_required
def page_list():
    pages = Page.query.order_by(Page.slug.asc()).all()
    return render_template("admin/pages/index.html", pages=pages)


@admin_bp.route("/pages/<slug>/edit", methods=["GET", "POST"])
@admin_required
def page_edit(slug):
    page = Page.query.filter_by(slug=slug).first_or_404()
    if request.method == "POST":
        page.title = request.form.get("title", "").strip()
        page.content = request.form.get("content", "").strip()
        page.is_active = bool(request.form.get("is_active"))

        db.session.commit()
        cache.invalidate_all()
        flash(f"Page '{page.title}' updated successfully!", "success")
        return redirect(url_for("admin.page_list"))

    return render_template("admin/pages/form.html", page=page)


# ==============================================================================
# STORE SETTINGS
# ==============================================================================

@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    """Store settings: brand name, logo, phone, WhatsApp, email, address, UPI, COD toggle, GST."""
    if request.method == "POST":
        # Text fields
        keys = [
            "company_name",
            "tagline",
            "support_phone",
            "support_whatsapp",
            "support_email",
            "store_address",
            "upi_id",
            "delivery_charge",
            "free_delivery_threshold",
            "cod_enabled",
            "gst_number",
            "instagram_url",
            "footer_text",
            "admin_secret_slug",
        ]
        for k in keys:
            if k in request.form:
                Setting.set_value(k, request.form.get(k, "").strip())

        # Handle UPI QR Code Upload
        qr_file = request.files.get("upi_qr_file")
        if qr_file and qr_file.filename:
            try:
                qr_key = handle_uploaded_file(qr_file, prefix="qr")
                Setting.set_value("upi_qr_url", f"/static/uploads/{qr_key}")
            except ValueError as ve:
                flash(str(ve), "error")

        db.session.commit()
        cache.invalidate_all()
        flash("Store settings updated successfully! Reflecting live immediately.", "success")
        return redirect(url_for("admin.settings"))

    all_settings = Setting.get_all_dict()
    return render_template("admin/settings/index.html", settings=all_settings)


# ==============================================================================
# ADMIN SECURITY & 2FA CONFIGURATION
# ==============================================================================

@admin_bp.route("/security", methods=["GET", "POST"])
@admin_required
def security():
    """Admin security management: 2FA / TOTP configuration, secret URL, and session controls."""
    admin = db.session.get(Admin, session["admin_id"])
    brand_name = Setting.get_value("company_name", "Scented Bubbles")
    from app.services.totp_service import generate_totp_secret, verify_totp, get_totp_uri

    # Generate setup secret for display if 2FA is not enabled yet
    setup_secret = session.get("admin_setup_totp_secret")
    if not setup_secret or admin.is_2fa_enabled:
        setup_secret = generate_totp_secret()
        session["admin_setup_totp_secret"] = setup_secret

    totp_uri = get_totp_uri(setup_secret, admin.username, issuer=brand_name)

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "enable_2fa":
            code = request.form.get("code", "").strip()
            secret_to_verify = session.get("admin_setup_totp_secret", "")
            if verify_totp(secret_to_verify, code):
                admin.totp_secret = secret_to_verify
                admin.is_2fa_enabled = True
                db.session.commit()
                session.pop("admin_setup_totp_secret", None)
                flash("Two-factor authentication has been successfully enabled for your account!", "success")
                return redirect(url_for("admin.security"))
            else:
                flash("Invalid verification code. Please enter the 6-digit code shown in your authenticator app.", "error")

        elif action == "disable_2fa":
            password = request.form.get("password", "")
            if admin.check_password(password):
                admin.is_2fa_enabled = False
                admin.totp_secret = None
                db.session.commit()
                flash("Two-factor authentication has been disabled.", "info")
                return redirect(url_for("admin.security"))
            else:
                flash("Incorrect password. 2FA was not disabled.", "error")

        elif action == "update_secret_slug":
            slug = request.form.get("admin_secret_slug", "").strip()
            Setting.set_value("admin_secret_slug", slug)
            db.session.commit()
            cache.invalidate_all()
            if slug:
                flash(f"Secret admin access key updated! Access URL: /admin/login?key={slug}", "success")
            else:
                flash("Secret admin key removed. Standard access enabled.", "info")
            return redirect(url_for("admin.security"))

    secret_slug = Setting.get_value("admin_secret_slug", "")

    return render_template(
        "admin/security/index.html",
        admin=admin,
        setup_secret=setup_secret,
        totp_uri=totp_uri,
        secret_slug=secret_slug,
        brand_name=brand_name,
    )

