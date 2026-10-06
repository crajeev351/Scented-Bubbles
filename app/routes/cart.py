from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify
from app.models.product_variants import ProductVariant
from app.models.settings import Setting
from app.services.order_service import calculate_delivery_charge

from app.extensions import csrf

cart_bp = Blueprint("cart", __name__)


@cart_bp.route("/cart")
def view_cart():
    """Renders client-side cart page hydrated via localStorage and /cart/summary."""
    return render_template("cart/index.html")


@cart_bp.route("/cart/summary", methods=["POST"])
@csrf.exempt
def cart_summary():
    """Single endpoint returning priced, stock-checked lines for display.
    Never trusts browser prices; re-queries database for all variant prices and stocks.
    """
    data = request.get_json(silent=True) or {}
    items_input = data.get("items", [])

    lines = []
    subtotal = Decimal("0.00")
    all_in_stock = True

    # Consolidate multiple line items of the same variant_id
    qty_by_variant = {}
    for it in items_input:
        try:
            vid = int(it.get("variant_id"))
            qty = max(1, int(it.get("qty", 1)))
            qty_by_variant[vid] = qty_by_variant.get(vid, 0) + qty
        except (ValueError, TypeError):
            continue

    if qty_by_variant:
        variants = ProductVariant.query.filter(ProductVariant.id.in_(qty_by_variant.keys())).all()
        variant_map = {v.id: v for v in variants}

        for vid, requested_qty in qty_by_variant.items():
            variant = variant_map.get(vid)
            if not variant or variant.is_deleted or not variant.active:
                lines.append({
                    "variant_id": vid,
                    "product_name": "Unavailable Product",
                    "size_label": "",
                    "sku": "",
                    "price": "0.00",
                    "effective_price": "0.00",
                    "qty": requested_qty,
                    "line_total": "0.00",
                    "image_url": "/static/images/placeholder_perfume.webp",
                    "in_stock": False,
                    "available_stock": 0,
                    "error": "This item is no longer available.",
                })
                all_in_stock = False
                continue

            product = variant.product
            eff_price = variant.effective_price
            line_total = eff_price * requested_qty
            subtotal += line_total

            item_in_stock = variant.stock >= requested_qty and variant.stock > 0
            if not item_in_stock:
                all_in_stock = False

            lines.append({
                "variant_id": variant.id,
                "product_id": product.id,
                "product_slug": product.slug,
                "product_name": product.name,
                "size_label": variant.size_label,
                "sku": variant.sku,
                "price": str(variant.price),
                "discounted_price": str(variant.discounted_price) if variant.discounted_price else None,
                "effective_price": str(eff_price),
                "qty": requested_qty,
                "line_total": str(line_total),
                "image_url": product.primary_image_url,
                "in_stock": item_in_stock,
                "available_stock": variant.stock,
                "discount_percentage": variant.discount_percentage,
            })

    delivery_fee = calculate_delivery_charge(subtotal)
    total_amount = subtotal + delivery_fee
    
    free_threshold = Decimal(str(Setting.get_value("free_delivery_threshold", "999.00")))
    remaining_for_free = max(Decimal("0.00"), free_threshold - subtotal)
    progress_pct = min(100, int((subtotal / free_threshold) * 100)) if free_threshold > 0 else 100

    return jsonify({
        "lines": lines,
        "subtotal": str(subtotal),
        "delivery_charge": str(delivery_fee),
        "total": str(total_amount),
        "free_delivery_threshold": str(free_threshold),
        "remaining_for_free_delivery": str(remaining_for_free),
        "free_delivery_progress": progress_pct,
        "is_valid": all_in_stock and len(lines) > 0,
        "item_count": sum(line["qty"] for line in lines),
    })
