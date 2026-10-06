from flask import Blueprint, render_template, request, jsonify, abort
from sqlalchemy.orm import selectinload
from sqlalchemy import or_
from app.models.products import Product
from app.models.categories import Category
from app.models.product_variants import ProductVariant
from app.models.combos import Combo

products_bp = Blueprint("products", __name__)


@products_bp.route("/products")
def product_list():
    """Server-side paginated product listing (12 per page) with indexed filters."""
    page = request.args.get("page", 1, type=int)
    category_slug = request.args.get("category", "").strip()
    search_query = request.args.get("q", "").strip()
    sort_by = request.args.get("sort", "newest").strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    in_stock_only = request.args.get("in_stock", type=bool)

    query = (
        Product.query.filter_by(active=True, is_deleted=False)
        .options(
            selectinload(Product.variants),
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.categories),
        )
    )

    selected_category = None
    if category_slug:
        selected_category = Category.query.filter_by(slug=category_slug, active=True, is_deleted=False).first()
        if selected_category:
            query = query.filter(
                or_(
                    Product.category_id == selected_category.id,
                    Product.categories.any(Category.id == selected_category.id),
                )
            )

    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Product.name.ilike(search_pattern),
                Product.inspired_by.ilike(search_pattern),
                Product.short_description.ilike(search_pattern),
            )
        )

    # Sorting
    if sort_by == "featured":
        query = query.order_by(Product.featured.desc(), Product.id.desc())
    elif sort_by == "bestseller":
        query = query.order_by(Product.bestseller.desc(), Product.id.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    pagination = query.paginate(page=page, per_page=12, error_out=False)
    categories = Category.query.filter_by(active=True, is_deleted=False).order_by(Category.display_order.asc()).all()

    return render_template(
        "products/list.html",
        products=pagination.items,
        pagination=pagination,
        categories=categories,
        selected_category=selected_category,
        search_query=search_query,
        sort_by=sort_by,
    )


@products_bp.route("/products/<slug>")
def product_detail(slug):
    """Product detail page with fragrance notes breakdown, variant selector, and related items."""
    product = (
        Product.query.filter_by(slug=slug, active=True, is_deleted=False)
        .options(
            selectinload(Product.variants),
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.categories),
        )
        .first_or_404()
    )

    # Fetch 4 related products in any shared category
    cat_ids = [c.id for c in product.categories] or ([product.category_id] if product.category_id else [])
    related_products = (
        Product.query.filter(
            or_(
                Product.category_id.in_(cat_ids),
                Product.categories.any(Category.id.in_(cat_ids)),
            ),
            Product.id != product.id,
            Product.active.is_(True),
            Product.is_deleted.is_(False),
        )
        .options(selectinload(Product.variants), selectinload(Product.images), selectinload(Product.categories))
        .distinct()
        .limit(4)
        .all()
    )

    return render_template(
        "products/detail.html",
        product=product,
        related_products=related_products,
    )


@products_bp.route("/categories/<slug>")
def category_detail(slug):
    """Category landing page directing to filtered catalog."""
    category = Category.query.filter_by(slug=slug, active=True, is_deleted=False).first_or_404()
    page = request.args.get("page", 1, type=int)
    
    query = (
        Product.query.filter(
            or_(
                Product.category_id == category.id,
                Product.categories.any(Category.id == category.id),
            ),
            Product.active.is_(True),
            Product.is_deleted.is_(False),
        )
        .options(selectinload(Product.variants), selectinload(Product.images), selectinload(Product.categories))
        .distinct()
        .order_by(Product.created_at.desc())
    )
    pagination = query.paginate(page=page, per_page=12, error_out=False)

    return render_template(
        "products/list.html",
        products=pagination.items,
        pagination=pagination,
        categories=Category.query.filter_by(active=True, is_deleted=False).all(),
        selected_category=category,
        search_query="",
        sort_by="newest",
    )


@products_bp.route("/combos")
def combo_list():
    """Curated fragrance combo packs."""
    combos = (
        Combo.query.filter_by(active=True, is_deleted=False)
        .options(selectinload(Combo.items))
        .order_by(Combo.display_order.asc())
        .all()
    )
    return render_template("products/combos.html", combos=combos)


@products_bp.route("/combos/<slug>")
def combo_detail(slug):
    """Combo detail view with breakdown of included perfumes/diffusers."""
    combo = (
        Combo.query.filter_by(slug=slug, active=True, is_deleted=False)
        .options(selectinload(Combo.items))
        .first_or_404()
    )
    return render_template("products/combo_detail.html", combo=combo)


@products_bp.route("/search")
def live_search():
    """Live debounced search endpoint.
    Per performance rules: returns strictly {id, name, slug, price, discounted_price, thumbnail, in_stock}.
    """
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify([])

    pattern = f"%{q}%"
    products = (
        Product.query.filter(
            Product.active.is_(True),
            Product.is_deleted.is_(False),
            or_(
                Product.name.ilike(pattern),
                Product.inspired_by.ilike(pattern),
                Product.short_description.ilike(pattern),
            ),
        )
        .options(selectinload(Product.variants), selectinload(Product.images))
        .limit(8)
        .all()
    )

    results = []
    for p in products:
        default_var = p.default_variant
        results.append({
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "inspired_by": p.inspired_by or "",
            "price": float(default_var.price) if default_var else 0.0,
            "discounted_price": float(default_var.discounted_price) if (default_var and default_var.discounted_price) else None,
            "thumbnail": p.primary_image_url,
            "in_stock": p.in_stock,
        })

    return jsonify(results)
