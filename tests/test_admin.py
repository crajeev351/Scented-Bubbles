from decimal import Decimal
import pytest
from app.extensions import db
from app.models.admins import Admin
from app.models.products import Product
from app.models.product_variants import ProductVariant
from app.models.orders import Order
from app.models.settings import Setting
from app.models.categories import Category
from app.services.cache_service import cache
from app.services.order_service import create_order, update_order_status, InvalidOrderStateError


@pytest.fixture
def admin_user(app):
    """Creates an active admin user."""
    with app.app_context():
        admin = Admin(username="head_admin", email="admin@scentedbubbles.com", is_active=True)
        admin.set_password("AdminSecurePassword123!")
        db.session.add(admin)
        db.session.commit()
        return admin.id


@pytest.fixture
def auth_client(client, admin_user):
    """Client with an active admin session."""
    with client.session_transaction() as sess:
        sess["admin_id"] = admin_user
        sess["admin_username"] = "head_admin"
    return client


def test_unauthorized_admin_access_redirects(client):
    """Unauthorized access to every /admin/* route must redirect to login."""
    protected_urls = [
        "/admin/",
        "/admin/dashboard",
        "/admin/products",
        "/admin/products/new",
        "/admin/categories",
        "/admin/categories/new",
        "/admin/combos",
        "/admin/combos/new",
        "/admin/banners",
        "/admin/banners/new",
        "/admin/orders",
        "/admin/customers",
        "/admin/pages",
        "/admin/settings",
    ]

    for url in protected_urls:
        res = client.get(url, follow_redirects=False)
        assert res.status_code == 302, f"Expected redirect for unauthorized access to {url}, got {res.status_code}"
        assert "/admin/login" in res.headers["Location"], f"Expected redirect to /admin/login for {url}"


def test_csrf_enforced_on_admin_post(app, admin_user):
    """CSRF must be enforced on admin POST requests when CSRF is active."""
    app.config["WTF_CSRF_ENABLED"] = True
    test_client = app.test_client()
    
    with test_client.session_transaction() as sess:
        sess["admin_id"] = admin_user
        sess["admin_username"] = "head_admin"

    # POST without CSRF token
    res = test_client.post("/admin/categories/new", data={
        "name": "Attar Oils",
        "slug": "attar-oils"
    })
    # Flask-WTF rejects with 400 Bad Request
    assert res.status_code == 400
    app.config["WTF_CSRF_ENABLED"] = False


def test_invalid_status_transitions_rejected(app, sample_catalog):
    """Enforce state machine: illegal order status transitions are rejected."""
    with app.app_context():
        vid = sample_catalog["variant_50ml_id"]
        order = create_order(
            cart_items=[{"variant_id": vid, "qty": 1}],
            customer_info={"phone": "9876543220", "name": "Status Test"},
            shipping_info={"name": "Status Test", "phone": "9876543220", "address_line1": "Street", "city": "City", "state": "State", "pincode": "500001"},
            payment_method="COD",
        )
        assert order.order_status == Order.STATUS_PENDING

        # Attempt illegal transition: PENDING -> SHIPPED (must go through CONFIRMED -> PACKED -> SHIPPED)
        with pytest.raises(InvalidOrderStateError):
            update_order_status(order.order_id, Order.STATUS_SHIPPED)

        # Attempt illegal transition: PENDING -> DELIVERED
        with pytest.raises(InvalidOrderStateError):
            update_order_status(order.order_id, Order.STATUS_DELIVERED)

        # Valid transition: PENDING -> CONFIRMED
        order_confirmed = update_order_status(order.order_id, Order.STATUS_CONFIRMED)
        assert order_confirmed.order_status == Order.STATUS_CONFIRMED


def test_reject_payment_cancels_order_and_restores_stock(auth_client, app, sample_catalog):
    """Admin rejecting payment sets status FAILED, cancels order, and restores stock."""
    with app.app_context():
        vid = sample_catalog["variant_50ml_id"]
        initial_stock = db.session.get(ProductVariant, vid).stock

        order = create_order(
            cart_items=[{"variant_id": vid, "qty": 2}],
            customer_info={"phone": "9876543221", "name": "Pay Test"},
            shipping_info={"name": "Pay Test", "phone": "9876543221", "address_line1": "Road 1", "city": "City", "state": "State", "pincode": "500001"},
            payment_method="MANUAL_UPI",
            utr="111122223333",
        )
        # Stock decremented by 2
        assert db.session.get(ProductVariant, vid).stock == initial_stock - 2

        # Admin rejects payment
        res = auth_client.post(f"/admin/orders/{order.order_id}/reject-payment", data={
            "reason": "Invalid fake UTR"
        }, follow_redirects=True)
        assert res.status_code == 200

        # Stock must be restored and order marked CANCELLED
        reloaded_order = Order.query.filter_by(order_id=order.order_id).first()
        assert reloaded_order.payment_status == Order.PAYMENT_FAILED
        assert reloaded_order.order_status == Order.STATUS_CANCELLED
        assert db.session.get(ProductVariant, vid).stock == initial_stock


def test_quick_variant_update_and_cache_invalidation(auth_client, app, sample_catalog):
    """Admin quick update modifies variant price and stock, and immediately invalidates cache."""
    vid = sample_catalog["variant_50ml_id"]
    
    with app.app_context():
        cache.set("home_data", {"dummy": "cached"})
        assert cache.get("home_data") is not None

    res = auth_client.post(f"/admin/products/variants/{vid}/quick-update", data={
        "price": "1599.00",
        "discounted_price": "1399.00",
        "stock": "42"
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        var = db.session.get(ProductVariant, vid)
        assert var.price == Decimal("1599.00")
        assert var.discounted_price == Decimal("1399.00")
        assert var.stock == 42
        # Cache must have been invalidated!
        assert cache.get("home_data") is None


def test_admin_settings_update_brand_name(auth_client, app):
    """Admin updates company_name; cache is invalidated and storefront reflects new brand name."""
    res = auth_client.post("/admin/settings", data={
        "company_name": "Scented Bubbles",
        "support_whatsapp": "919999888877",
        "support_email": "hello@scentedbubbles.com",
        "delivery_charge": "40.00",
        "free_delivery_threshold": "799.00",
        "cod_enabled": "true",
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        assert Setting.get_value("company_name") == "Scented Bubbles"
        assert Setting.get_value("delivery_charge") == "40.00"
        assert Setting.get_value("free_delivery_threshold") == "799.00"


def test_login_rate_limiting():
    """Admin login endpoint must enforce rate limiting (5 per minute)."""
    from app import create_app
    from app.extensions import db

    rate_limit_app = create_app("testing", {"RATELIMIT_ENABLED": True})
    with rate_limit_app.app_context():
        db.create_all()
        client = rate_limit_app.test_client()

        responses = []
        for _ in range(6):
            res = client.post("/admin/login", data={
                "username": "wrong_user",
                "password": "wrong_password"
            })
            responses.append(res.status_code)

        db.session.remove()
        db.drop_all()

    # The 6th request should hit the 429 Too Many Requests rate limit
    assert 429 in responses, f"Expected 429 in responses, got {responses}"


def test_admin_manual_checklist_flow(client, app, sample_catalog):
    """Full manual checklist verification:
    1. Admin logs in
    2. Adds product with 2 variants
    3. Changes price via quick update
    4. Places order on storefront
    5. Sees order in admin
    6. Transitions payment to PAID
    7. Cancels order
    8. Confirms stock restored
    """
    import json
    from app.models.categories import Category

    with app.app_context():
        # Create admin credentials
        admin = Admin(username="checklist_admin", email="checklist@scentedbubbles.com", is_active=True)
        admin.set_password("ChecklistPass789!")
        db.session.add(admin)
        db.session.commit()
        cat_id = sample_catalog["category_id"]

    # 1. Login
    login_res = client.post("/admin/login", data={
        "username": "checklist_admin",
        "password": "ChecklistPass789!"
    }, follow_redirects=True)
    assert login_res.status_code == 200
    assert b"Dashboard" in login_res.data or b"Analytics" in login_res.data

    # 2. Add product with 2 variants
    add_prod_res = client.post("/admin/products/new", data={
        "name": "Amber Rose Elixir",
        "category_id": cat_id,
        "short_description": "Luxurious floral oriental",
        "full_description": "Rich amber blend with damask rose.",
        "top_notes": "Damask Rose",
        "heart_notes": "Ambergris",
        "base_notes": "Vanilla",
        "variant_label[]": ["50ml EDP", "100ml EDP"],
        "variant_sku[]": ["ARE-50ML", "ARE-100ML"],
        "variant_price[]": ["1200.00", "2100.00"],
        "variant_discounted_price[]": ["1100.00", "1950.00"],
        "variant_stock[]": ["25", "15"],
        "active": "true"
    }, follow_redirects=True)
    assert add_prod_res.status_code == 200

    with app.app_context():
        new_prod = Product.query.filter_by(name="Amber Rose Elixir").first()
        assert new_prod is not None
        assert len(new_prod.variants) == 2
        v1 = [v for v in new_prod.variants if v.sku == "ARE-50ML"][0]
        v1_id = v1.id
        assert v1.stock == 25
        assert v1.price == Decimal("1200.00")

    # 3. Change price via quick-update
    quick_res = client.post(f"/admin/products/variants/{v1_id}/quick-update", data={
        "price": "1150.00",
        "discounted_price": "999.00",
        "stock": "25"
    }, follow_redirects=True)
    assert quick_res.status_code == 200

    with app.app_context():
        v1_updated = db.session.get(ProductVariant, v1_id)
        assert v1_updated.price == Decimal("1150.00")
        assert v1_updated.discounted_price == Decimal("999.00")

    # 4. Place order on storefront
    cart_json = json.dumps([{"variant_id": v1_id, "qty": 3}])
    checkout_res = client.post("/checkout", data={
        "cart_data": cart_json,
        "name": "Sonia Sharma",
        "phone": "9876543210",
        "address_line1": "42 Perfume Boulevard",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400001",
        "payment_method": "MANUAL_UPI",
        "utr": "UTR778899001122"
    }, follow_redirects=True)
    assert checkout_res.status_code == 200

    with app.app_context():
        # Stock must be decremented by 3 (25 -> 22)
        v1_after_order = db.session.get(ProductVariant, v1_id)
        assert v1_after_order.stock == 22

        order = Order.query.filter_by(shipping_phone="9876543210").order_by(Order.id.desc()).first()
        assert order is not None
        order_id = order.order_id
        assert order.payment_status == Order.PAYMENT_PENDING_VERIFICATION

    # 5. See order in admin
    admin_orders_res = client.get(f"/admin/orders?q={order_id}")
    assert admin_orders_res.status_code == 200
    assert order_id.encode("utf-8") in admin_orders_res.data

    detail_res = client.get(f"/admin/orders/{order_id}")
    assert detail_res.status_code == 200
    assert b"Sonia Sharma" in detail_res.data

    # 6. Transition payment to PAID
    verify_res = client.post(f"/admin/orders/{order_id}/verify-payment", data={
        "admin_notes": "Bank transfer verified via UPI"
    }, follow_redirects=True)
    assert verify_res.status_code == 200

    with app.app_context():
        paid_order = Order.query.filter_by(order_id=order_id).first()
        assert paid_order.payment_status == Order.PAYMENT_PAID

    # 7. Cancel order
    cancel_res = client.post(f"/admin/orders/{order_id}/cancel", data={
        "reason": "Customer cancellation request"
    }, follow_redirects=True)
    assert cancel_res.status_code == 200

    with app.app_context():
        cancelled_order = Order.query.filter_by(order_id=order_id).first()
        assert cancelled_order.order_status == Order.STATUS_CANCELLED

        # 8. Confirm stock restored back to 25
        v1_restored = db.session.get(ProductVariant, v1_id)
        assert v1_restored.stock == 25


def test_category_archive_unarchive_and_permanent_delete(app, auth_client):
    """Test archiving, viewing archived categories, unarchiving, and permanent deletion."""
    with app.app_context():
        cat = Category(
            name="Testing Diffusers",
            slug="testing-diffusers",
            description="Aromatherapy diffusers",
            active=True,
            is_deleted=False,
        )
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    # 1. Category is visible in admin list
    res = auth_client.get("/admin/categories")
    assert res.status_code == 200
    assert b"Testing Diffusers" in res.data
    assert b"Archive" in res.data

    # 2. Archive category
    archive_res = auth_client.post(f"/admin/categories/{cat_id}/archive", follow_redirects=True)
    assert archive_res.status_code == 200
    assert b"archived" in archive_res.data.lower()

    with app.app_context():
        archived_cat = db.session.get(Category, cat_id)
        assert archived_cat.is_deleted is True
        assert archived_cat.active is False

    # 3. Archived category remains visible in category list with Unarchive button
    list_res = auth_client.get("/admin/categories")
    assert list_res.status_code == 200
    assert b"Testing Diffusers" in list_res.data
    assert b"Unarchive" in list_res.data

    # Check filter tabs: should appear under ?status=archived
    archived_tab_res = auth_client.get("/admin/categories?status=archived")
    assert archived_tab_res.status_code == 200
    assert b"Testing Diffusers" in archived_tab_res.data

    # And should NOT appear under ?status=active
    active_tab_res = auth_client.get("/admin/categories?status=active")
    assert active_tab_res.status_code == 200
    assert b"Testing Diffusers" not in active_tab_res.data

    # 4. Unarchive category
    unarchive_res = auth_client.post(f"/admin/categories/{cat_id}/unarchive", follow_redirects=True)
    assert unarchive_res.status_code == 200
    assert b"unarchived" in unarchive_res.data.lower()

    with app.app_context():
        restored_cat = db.session.get(Category, cat_id)
        assert restored_cat.is_deleted is False
        assert restored_cat.active is True

    # 5. Permanent delete category (when no products linked)
    del_res = auth_client.post(f"/admin/categories/{cat_id}/delete", follow_redirects=True)
    assert del_res.status_code == 200
    assert b"permanently deleted" in del_res.data.lower()

    with app.app_context():
        deleted_cat = db.session.get(Category, cat_id)
        assert deleted_cat is None


def test_category_prevent_delete_when_products_linked(app, auth_client, sample_catalog):
    """Cannot permanently delete a category if products are assigned to it."""
    with app.app_context():
        prod = db.session.get(Product, sample_catalog["product_id"])
        cat_id = prod.category_id

    # Try to permanently delete category that has products
    del_res = auth_client.post(f"/admin/categories/{cat_id}/delete", follow_redirects=True)
    assert del_res.status_code == 200
    assert b"Cannot delete category" in del_res.data or b"assigned to it" in del_res.data

    with app.app_context():
        cat = db.session.get(Category, cat_id)
        assert cat is not None


def test_category_duplicate_slug_archived_warning(app, auth_client):
    """Creating a category with a slug that matches an archived category shows a clear warning."""
    with app.app_context():
        cat = Category(
            name="Room Sprays",
            slug="room-sprays",
            active=False,
            is_deleted=True,
        )
        db.session.add(cat)
        db.session.commit()

    # Attempt to create new category with the same slug
    create_res = auth_client.post("/admin/categories/new", data={
        "name": "Room Sprays Duplicate",
        "slug": "room-sprays",
    }, follow_redirects=True)
    assert create_res.status_code == 200
    assert b"already exists in archives" in create_res.data


def test_product_multiple_categories_create_and_edit(app, auth_client):
    """Test assigning multiple categories to a single product during creation and editing."""
    with app.app_context():
        c1 = Category(name="Fine Fragrances", slug="fine-fragrances", active=True)
        c2 = Category(name="For Him", slug="for-him", active=True)
        c3 = Category(name="Discovery Sets", slug="discovery-sets", active=True)
        db.session.add_all([c1, c2, c3])
        db.session.commit()
        c1_id, c2_id, c3_id = c1.id, c2.id, c3.id

    # 1. Create product belonging to both Fine Fragrances and For Him
    create_res = auth_client.post("/admin/products/new", data={
        "name": "Balmain Paris Special",
        "slug": "balmain-paris-special",
        "category_ids": [str(c1_id), str(c2_id)],
        "short_description": "Luxury French fragrance",
        "variant_label[]": ["50ml EDP"],
        "variant_sku[]": ["BPS-50ML"],
        "variant_price[]": ["1899.00"],
        "variant_stock[]": ["10"],
    }, follow_redirects=True)
    assert create_res.status_code == 200
    assert b"created successfully" in create_res.data.lower()

    with app.app_context():
        prod = Product.query.filter_by(slug="balmain-paris-special").first()
        assert prod is not None
        assigned_cat_ids = [c.id for c in prod.categories]
        assert c1_id in assigned_cat_ids
        assert c2_id in assigned_cat_ids
        assert len(assigned_cat_ids) == 2
        prod_id = prod.id

    # 2. View storefront category detail for both categories
    res_c1 = auth_client.get("/categories/fine-fragrances")
    assert res_c1.status_code == 200
    assert b"Balmain Paris Special" in res_c1.data

    res_c2 = auth_client.get("/categories/for-him")
    assert res_c2.status_code == 200
    assert b"Balmain Paris Special" in res_c2.data

    # Should NOT be in discovery-sets yet
    res_c3 = auth_client.get("/categories/discovery-sets")
    assert res_c3.status_code == 200
    assert b"Balmain Paris Special" not in res_c3.data

    # 3. Edit product to also include Discovery Sets
    edit_res = auth_client.post(f"/admin/products/{prod_id}/edit", data={
        "name": "Balmain Paris Special",
        "slug": "balmain-paris-special",
        "category_ids": [str(c1_id), str(c2_id), str(c3_id)],
        "short_description": "Luxury French fragrance updated",
        "active": "1",
    }, follow_redirects=True)
    assert edit_res.status_code == 200

    with app.app_context():
        updated_prod = db.session.get(Product, prod_id)
        updated_cat_ids = [c.id for c in updated_prod.categories]
        assert len(updated_cat_ids) == 3
        assert c1_id in updated_cat_ids
        assert c2_id in updated_cat_ids
        assert c3_id in updated_cat_ids

    # 4. Now appears in discovery-sets too
    res_c3_after = auth_client.get("/categories/discovery-sets")
    assert res_c3_after.status_code == 200
    assert b"Balmain Paris Special" in res_c3_after.data


def test_product_inspired_by_field_and_search(app, auth_client):
    """Test inspired_by field creation, editing, detail view, catalog search and live search."""
    with app.app_context():
        cat = Category(name="Fine Fragrances", slug="fine-fragrances", active=True)
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    # 1. Create a clone perfume with a creative product name and "inspired by gucci flora"
    create_res = auth_client.post("/admin/products/new", data={
        "name": "Gardenia Blossom Luxe",
        "slug": "gardenia-blossom-luxe",
        "category_ids": [str(cat_id)],
        "inspired_by": "Gucci Flora Gorgeous Gardenia",
        "short_description": "Delicate white floral clone",
        "active": "1",
        "variant_label[]": ["50ml EDP"],
        "variant_sku[]": ["GBL-50ML"],
        "variant_price[]": ["1499.00"],
        "variant_stock[]": ["20"],
    }, follow_redirects=True)
    assert create_res.status_code == 200

    with app.app_context():
        prod = Product.query.filter_by(slug="gardenia-blossom-luxe").first()
        assert prod is not None
        assert prod.inspired_by == "Gucci Flora Gorgeous Gardenia"
        prod_id = prod.id

    # 2. Search catalog by inspired_by brand "Gucci"
    search_res = auth_client.get("/products?q=Gucci")
    assert search_res.status_code == 200
    assert b"Gardenia Blossom Luxe" in search_res.data
    assert b"Gucci Flora" in search_res.data

    # 3. Live search /search?q=gucci
    live_res = auth_client.get("/search?q=gucci")
    assert live_res.status_code == 200
    live_data = live_res.get_json()
    assert len(live_data) >= 1
    matched = next((item for item in live_data if item["slug"] == "gardenia-blossom-luxe"), None)
    assert matched is not None
    assert "Gucci Flora" in matched["inspired_by"]

    # 4. View product detail page shows inspired_by badge, no notes breakdown, and no family
    detail_res = auth_client.get("/products/gardenia-blossom-luxe")
    assert detail_res.status_code == 200
    assert b"Gucci Flora Gorgeous Gardenia" in detail_res.data
    assert b"Olfactory Structure &amp; Notes" not in detail_res.data
    assert b"Family:" not in detail_res.data

    # Check admin edit form: no notes fields or fragrance family
    form_res = auth_client.get(f"/admin/products/{prod_id}/edit")
    assert form_res.status_code == 200
    assert b"Top Notes" not in form_res.data
    assert b"Heart Notes" not in form_res.data
    assert b"Base Notes" not in form_res.data
    assert b"Fragrance Family" not in form_res.data
    assert b"Inspired By" in form_res.data

    # Check admin list: 'Inspired By' header without '/ Notes'
    list_res = auth_client.get("/admin/products")
    assert list_res.status_code == 200
    assert b"Inspired By</th>" in list_res.data
    assert b"Inspired By / Notes" not in list_res.data

    # 5. Edit inspired_by field
    edit_res = auth_client.post(f"/admin/products/{prod_id}/edit", data={
        "name": "Gardenia Blossom Luxe",
        "slug": "gardenia-blossom-luxe",
        "category_ids": [str(cat_id)],
        "inspired_by": "Gucci Flora Emerald",
        "active": "1",
    }, follow_redirects=True)
    assert edit_res.status_code == 200

    with app.app_context():
        updated = db.session.get(Product, prod_id)
        assert updated.inspired_by == "Gucci Flora Emerald"


def test_product_low_stock_and_out_of_stock_frontend_alerts(app, auth_client, client):
    """Test frontend advertising banner for low stock and out-of-stock messages when stock updated."""
    with app.app_context():
        cat = Category(name="Signature Line", slug="signature-line", active=True)
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    # 1. Create product with low stock (3 units)
    create_res = auth_client.post("/admin/products/new", data={
        "name": "Amber Noir Intense",
        "slug": "amber-noir-intense",
        "category_ids": [str(cat_id)],
        "inspired_by": "Tom Ford Noir de Noir",
        "short_description": "Dark oriental rose and truffle blend",
        "active": "1",
        "variant_label[]": ["100ml EDP"],
        "variant_sku[]": ["ANI-100ML"],
        "variant_price[]": ["1899.00"],
        "variant_stock[]": ["3"],
    }, follow_redirects=True)
    assert create_res.status_code == 200

    with app.app_context():
        prod = Product.query.filter_by(slug="amber-noir-intense").first()
        assert prod is not None
        v = prod.variants[0]
        var_id = v.id
        assert v.stock == 3
        assert v.is_low_stock is True

    # 2. Frontend shopper visits product detail page: sees Low Stock advertising urgency banner
    detail_res = client.get("/products/amber-noir-intense")
    assert detail_res.status_code == 200
    assert b"HURRY! LIMITED QUANTITY AVAILABLE" in detail_res.data
    assert b"Low Stock &bull; Only <span id=\"low-stock-count\">3</span> left" in detail_res.data
    assert b"Only 3 left" in detail_res.data
    assert b"Add to Bag" in detail_res.data

    # Catalog page shows Low Stock badge
    cat_res = client.get("/products")
    assert cat_res.status_code == 200
    assert b"Low Stock" in cat_res.data

    # 3. Admin updates stock to 0 (out of stock)
    stock_zero_res = auth_client.post(f"/admin/products/variants/{var_id}/quick-update", data={
        "stock": "0",
    }, follow_redirects=True)
    assert stock_zero_res.status_code == 200

    # 4. Frontend shopper reloads product detail page: sees Out of Stock message and disabled buttons
    detail_res_oos = client.get("/products/amber-noir-intense")
    assert detail_res_oos.status_code == 200
    assert b"Out of Stock (Currently Unavailable)" in detail_res_oos.data
    assert b"THIS SIZE IS CURRENTLY OUT OF STOCK" in detail_res_oos.data
    assert b"Out of Stock" in detail_res_oos.data

    # Catalog shows Out of Stock badge and disabled action
    cat_res_oos = client.get("/products")
    assert cat_res_oos.status_code == 200
    assert b"Out of Stock" in cat_res_oos.data

    # 5. Admin restocks product to 25 units (healthy stock)
    restock_res = auth_client.post(f"/admin/products/variants/{var_id}/quick-update", data={
        "stock": "25",
    }, follow_redirects=True)
    assert restock_res.status_code == 200

    # Frontend shows In Stock (Ready to Dispatch)
    detail_res_healthy = client.get("/products/amber-noir-intense")
    assert detail_res_healthy.status_code == 200
    assert b"In Stock (Ready to Dispatch)" in detail_res_healthy.data
    assert b"Add to Bag" in detail_res_healthy.data


def test_category_background_image_upload_and_auto_fit(app, client, auth_client):
    """Admin can upload a background image for category cards. Mismatched dimensions (e.g. portrait 400x800)
    are automatically center-cropped and fitted to 16:9 (800x450). Admin can also remove the image."""
    import io
    from PIL import Image
    from app.services.storage import get_storage

    # 1. Prepare mismatched portrait image (400 width x 800 height, aspect ratio 1:2 instead of 16:9)
    img_buf = io.BytesIO()
    test_img = Image.new("RGB", (400, 800), color=(140, 100, 60))
    test_img.save(img_buf, format="JPEG")
    img_buf.seek(0)

    # 2. Admin creates category with this image
    create_res = auth_client.post("/admin/categories/new", data={
        "name": "Amber & Woods",
        "slug": "amber-woods",
        "description": "Rich oud and precious woods.",
        "display_order": "1",
        "active": "1",
        "image": (img_buf, "amber_woods_portrait.jpg"),
    }, follow_redirects=True)
    assert create_res.status_code == 200

    with app.app_context():
        cat = Category.query.filter_by(slug="amber-woods").first()
        assert cat is not None
        assert cat.image_url is not None
        saved_img_key = cat.image_url
        cat_id = cat.id

        # Verify the saved image was cropped and scaled to exact aspect ratio (16:9)
        storage = get_storage()
        img_path = storage.upload_dir / saved_img_key
        assert img_path.exists()
        with Image.open(img_path) as saved_img:
            # Check aspect ratio is approximately 16:9 (800x450, ratio ~ 1.777)
            ratio = saved_img.width / saved_img.height
            assert abs(ratio - (16.0 / 9.0)) < 0.05
            assert saved_img.format == "WEBP"

    # 3. Storefront homepage renders category card with background image and 'has-bg-image' class
    home_res = client.get("/")
    assert home_res.status_code == 200
    assert b"Amber &amp; Woods" in home_res.data or b"Amber & Woods" in home_res.data
    assert b"has-bg-image" in home_res.data

    # 4. Admin edits category and removes background image
    edit_res = auth_client.post(f"/admin/categories/{cat_id}/edit", data={
        "name": "Amber & Woods",
        "slug": "amber-woods",
        "description": "Rich oud and precious woods.",
        "display_order": "1",
        "active": "1",
        "remove_image": "1",
    }, follow_redirects=True)
    assert edit_res.status_code == 200

    with app.app_context():
        updated_cat = Category.query.get(cat_id)
        assert updated_cat.image_url is None

    # Homepage still renders category, but without the removed image URL
    home_res2 = client.get("/")
    assert home_res2.status_code == 200
    assert saved_img_key.encode() not in home_res2.data


def test_hero_banner_image_upload_and_auto_fit(app, client, auth_client):
    """Admin can upload a hero banner image. Mismatched dimensions (e.g. 500x500 square)
    are automatically center-cropped and fitted to banner ratio (1920x600, 3.2:1)."""
    import io
    from PIL import Image
    from app.models.banners import Banner
    from app.services.storage import get_storage

    # 1. Prepare square image (500x500)
    img_buf = io.BytesIO()
    test_img = Image.new("RGB", (500, 500), color=(50, 40, 80))
    test_img.save(img_buf, format="JPEG")
    img_buf.seek(0)

    # 2. Admin creates hero banner
    create_res = auth_client.post("/admin/banners/new", data={
        "title": "Autumn Splendor",
        "subtitle": "Discover seasonal warmth",
        "link_url": "/products",
        "display_order": "1",
        "active": "1",
        "image": (img_buf, "autumn_square.jpg"),
    }, follow_redirects=True)
    assert create_res.status_code == 200

    with app.app_context():
        banner = Banner.query.filter_by(title="Autumn Splendor").first()
        assert banner is not None
        assert banner.image_key is not None
        assert "placeholder" not in banner.image_key

        # Verify auto-fitting
        storage = get_storage()
        img_path = storage.upload_dir / banner.image_key
        assert img_path.exists()
        with Image.open(img_path) as saved_img:
            # Banner ratio: 1920x600 = 3.2:1
            ratio = saved_img.width / saved_img.height
            assert abs(ratio - 3.2) < 0.1
            assert saved_img.format == "WEBP"

    # Homepage renders the banner
    home_res = client.get("/")
    assert home_res.status_code == 200
    assert b"Autumn Splendor" in home_res.data


def test_custom_hero_banner_with_product_and_combo_linking_and_overlay(app, client, auth_client):
    """Admin can create custom The Man Company-style banners linking directly to specific products or combos
    with custom button labels, taglines, and dark luxury overlays."""
    from app.models.banners import Banner
    from app.models.products import Product
    from app.models.combos import Combo

    with app.app_context():
        # Setup product and combo
        prod = Product(
            name="Sovereign Oud",
            slug="sovereign-oud",
            short_description="Regal amber and aged agarwood.",
            full_description="A majestic masterpiece.",
            is_deleted=False,
        )
        db.session.add(prod)

        combo = Combo(
            name="Curated Trio Pack",
            slug="curated-trio-pack",
            short_description="Select any 3 luxury perfumes.",
            full_description="The ultimate discovery experience.",
            combo_price=Decimal("1099.00"),
            is_deleted=False,
        )
        db.session.add(combo)
        db.session.commit()
        prod_id = prod.id
        combo_id = combo.id

    # 1. Admin creates custom hero banner linking to specific Product
    create_res = auth_client.post("/admin/banners/new", data={
        "tagline": "WHAT'S YOUR MOOD TODAY?",
        "title": "Buy Any 3 Perfumes @ ₹1,099",
        "subtitle": "Artisanal fine fragrances inspired by iconic originals.",
        "target_type": "product",
        "product_id": str(prod_id),
        "button_text": "BUY NOW @ ₹1,099",
        "secondary_button_text": "EXPLORE ALL",
        "secondary_button_link": "/combos",
        "overlay_opacity": "65",
        "display_order": "1",
        "active": "1",
    }, follow_redirects=True)
    assert create_res.status_code == 200

    with app.app_context():
        banner = Banner.query.filter_by(title="Buy Any 3 Perfumes @ ₹1,099").first()
        assert banner is not None
        assert banner.tagline == "WHAT'S YOUR MOOD TODAY?"
        assert banner.button_text == "BUY NOW @ ₹1,099"
        assert banner.target_type == "product"
        assert banner.target_id == prod_id
        assert banner.resolved_link_url == "/products/sovereign-oud"
        assert banner.overlay_opacity == 65
        banner_id = banner.id

    # 2. Verify Storefront homepage renders custom tagline, button, and direct product link
    home_res = client.get("/")
    assert home_res.status_code == 200
    assert b"WHAT&#39;S YOUR MOOD TODAY?" in home_res.data or b"WHAT'S YOUR MOOD TODAY?" in home_res.data
    assert b"Buy Any 3 Perfumes @ \xe2\x82\xb91,099" in home_res.data or b"Buy Any 3 Perfumes @ &#8377;1,099" in home_res.data or b"Buy Any 3 Perfumes" in home_res.data
    assert b"BUY NOW @ &#8377;1,099" in home_res.data or b"BUY NOW @ \xe2\x82\xb91,099" in home_res.data or b"BUY NOW" in home_res.data
    assert b"/products/sovereign-oud" in home_res.data
    assert b"EXPLORE ALL" in home_res.data
    assert b"/combos" in home_res.data

    # 3. Admin switches banner destination to Combo
    edit_res = auth_client.post(f"/admin/banners/{banner_id}/edit", data={
        "tagline": "LIMITED FESTIVE DEAL",
        "title": "Exclusive Curated Trio",
        "subtitle": "Grab 3 bottles for just ₹1,099.",
        "target_type": "combo",
        "combo_id": str(combo_id),
        "button_text": "CLAIM COMBO NOW",
        "overlay_opacity": "70",
        "display_order": "1",
        "active": "1",
    }, follow_redirects=True)
    assert edit_res.status_code == 200

    with app.app_context():
        updated_banner = db.session.get(Banner, banner_id)
        assert updated_banner.target_type == "combo"
        assert updated_banner.target_id == combo_id
        assert updated_banner.resolved_link_url == "/combos/curated-trio-pack"
        assert updated_banner.button_text == "CLAIM COMBO NOW"

    # Storefront homepage reflects the new combo link & button text
    home_res2 = client.get("/")
    assert home_res2.status_code == 200
    assert b"/combos/curated-trio-pack" in home_res2.data
    assert b"CLAIM COMBO NOW" in home_res2.data


def test_combo_create_and_edit_multiple_products(app, client, auth_client):
    """Admin can create a combo with multiple products/variants (e.g. 4 products) and edit it to 5."""
    from app.models.combos import Combo
    from app.models.products import Product
    from app.models.product_variants import ProductVariant

    with app.app_context():
        # Create 5 distinct products with variants
        variant_ids = []
        for i in range(1, 6):
            prod = Product(
                name=f"Perfume Sample {i}",
                slug=f"perfume-sample-{i}",
                short_description=f"Sample note {i}",
                is_deleted=False,
            )
            db.session.add(prod)
            db.session.flush()

            var = ProductVariant(
                product_id=prod.id,
                size_label="50ml",
                sku=f"SMPL-{i}-50ML",
                price=Decimal("699.00"),
                stock=20,
                active=True,
            )
            db.session.add(var)
            db.session.flush()
            variant_ids.append(var.id)
        db.session.commit()

    # 1. Admin creates a 4-product combo
    create_res = auth_client.post("/admin/combos/new", data={
        "name": "Luxury Quad Selection",
        "slug": "luxury-quad-selection",
        "combo_price": "1999.00",
        "short_description": "Four artisanal scents in one exclusive bundle.",
        "full_description": "The perfect luxury discovery gift box.",
        "display_order": "1",
        "active": "1",
        "variant_id[]": [str(v) for v in variant_ids[:4]],
        "quantity[]": ["1", "1", "1", "1"],
    }, follow_redirects=True)
    assert create_res.status_code == 200

    with app.app_context():
        combo = Combo.query.filter_by(slug="luxury-quad-selection").first()
        assert combo is not None
        assert len(combo.items) == 4
        # Original price = 4 * 699 = 2796.00
        assert combo.original_price == Decimal("2796.00")
        assert combo.savings == Decimal("797.00")
        assert combo.in_stock is True
        combo_id = combo.id

    # 2. Storefront combo detail page displays all 4 products
    detail_res = client.get("/combos/luxury-quad-selection")
    assert detail_res.status_code == 200
    for i in range(1, 5):
        assert f"Perfume Sample {i}".encode() in detail_res.data

    # 3. Admin edits the combo to include all 5 products
    edit_res = auth_client.post(f"/admin/combos/{combo_id}/edit", data={
        "name": "Grand Quintet Collection",
        "slug": "grand-quintet-collection",
        "combo_price": "2399.00",
        "short_description": "Five artisanal scents in one bundle.",
        "full_description": "The ultimate discovery suite.",
        "display_order": "1",
        "active": "1",
        "variant_id[]": [str(v) for v in variant_ids],
        "quantity[]": ["1", "1", "1", "1", "1"],
    }, follow_redirects=True)
    assert edit_res.status_code == 200

    with app.app_context():
        updated_combo = db.session.get(Combo, combo_id)
        assert updated_combo.name == "Grand Quintet Collection"
        assert len(updated_combo.items) == 5
        # Original price = 5 * 699 = 3495.00
        assert updated_combo.original_price == Decimal("3495.00")
        assert updated_combo.savings == Decimal("1096.00")

    # Storefront detail page now displays all 5 products
    detail_res2 = client.get("/combos/grand-quintet-collection")
    assert detail_res2.status_code == 200
    for i in range(1, 6):
        assert f"Perfume Sample {i}".encode() in detail_res2.data


def test_admin_order_delete_and_purge(auth_client, app, sample_catalog):
    """Admin can permanently delete single orders and bulk-purge all delivered orders to save storage."""
    phone = "9876543299"
    with app.app_context():
        order1 = create_order(
            cart_items=[{"variant_id": sample_catalog["variant_50ml_id"], "qty": 1}],
            customer_info={"name": "Kavita Rao", "phone": phone, "email": "kavita@example.com"},
            shipping_info={
                "name": "Kavita Rao",
                "phone": phone,
                "address_line1": "Road 10, Banjara Hills",
                "city": "Hyderabad",
                "state": "Telangana",
                "pincode": "500034",
            },
            payment_method="COD",
        )
        oid1 = order1.order_id

        order2 = create_order(
            cart_items=[{"variant_id": sample_catalog["variant_50ml_id"], "qty": 1}],
            customer_info={"name": "Rohan Mehra", "phone": "9876543298", "email": "rohan@example.com"},
            shipping_info={
                "name": "Rohan Mehra",
                "phone": "9876543298",
                "address_line1": "Sector 14",
                "city": "Gurugram",
                "state": "Haryana",
                "pincode": "122001",
            },
            payment_method="COD",
        )
        oid2 = order2.order_id

        # Mark order2 as DELIVERED
        update_order_status(oid2, "CONFIRMED")
        update_order_status(oid2, "PACKED")
        update_order_status(oid2, "SHIPPED", courier_name="BlueDart", tracking_number="BLU123456")
        update_order_status(oid2, "DELIVERED")

    # 1. Admin single delete on order1
    del_res = auth_client.post(f"/admin/orders/{oid1}/delete", follow_redirects=True)
    assert del_res.status_code == 200
    assert b"permanently deleted" in del_res.data

    with app.app_context():
        assert Order.query.filter_by(order_id=oid1).first() is None

    # 2. Admin bulk purge on delivered orders
    purge_res = auth_client.post("/admin/orders/purge-delivered", follow_redirects=True)
    assert purge_res.status_code == 200
    assert b"Successfully purged" in purge_res.data

    with app.app_context():
        assert Order.query.filter_by(order_id=oid2).first() is None








