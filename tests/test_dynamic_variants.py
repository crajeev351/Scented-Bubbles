from decimal import Decimal
import pytest
from app.extensions import db
from app.models.admins import Admin
from app.models.products import Product
from app.models.product_variants import ProductVariant
from app.models.categories import Category


@pytest.fixture
def admin_user(app):
    """Creates an active admin user."""
    with app.app_context():
        admin = Admin(username="perfume_owner", email="owner@scentedbubbles.com", is_active=True)
        admin.set_password("AdminSecurePassword123!")
        db.session.add(admin)
        db.session.commit()
        return admin.id


@pytest.fixture
def auth_client(client, admin_user):
    """Client with an active admin session."""
    with client.session_transaction() as sess:
        sess["admin_id"] = admin_user
        sess["admin_username"] = "perfume_owner"
    return client


def test_dynamic_ml_variants_creation_and_editing(app, auth_client):
    """Test owner can dynamically add different ML sizes, edit labels, delete variants, and add more."""
    with app.app_context():
        cat = Category(name="Fine Fragrances", slug="fine-fragrances", active=True)
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    # 1. Create a product with 4 dynamic ML sizes (10ml, 30ml, 50ml, 100ml)
    create_res = auth_client.post("/admin/products/new", data={
        "name": "Oud Wood Royale",
        "slug": "oud-wood-royale",
        "category_ids": [str(cat_id)],
        "short_description": "Smoky exotic woods and warm spices",
        "full_description": "A dark, refined scent capturing the essence of pure agarwood.",
        "active": "1",
        "variant_label[]": ["10ml Travel Spray", "30ml EDP", "50ml EDP", "100ml Extrait"],
        "variant_sku[]": ["OWR-10ML", "OWR-30ML", "OWR-50ML", "OWR-100ML"],
        "variant_price[]": ["499.00", "999.00", "1599.00", "2899.00"],
        "variant_discounted_price[]": ["399.00", "899.00", "1399.00", ""],
        "variant_stock[]": ["50", "30", "20", "10"],
    }, follow_redirects=True)
    assert create_res.status_code == 200

    with app.app_context():
        prod = Product.query.filter_by(slug="oud-wood-royale").first()
        assert prod is not None
        assert len(prod.variants) == 4
        labels = [v.size_label for v in prod.variants]
        assert "10ml Travel Spray" in labels
        assert "30ml EDP" in labels
        assert "50ml EDP" in labels
        assert "100ml Extrait" in labels

        v10 = [v for v in prod.variants if v.size_label == "10ml Travel Spray"][0]
        v30 = [v for v in prod.variants if v.size_label == "30ml EDP"][0]
        v100 = [v for v in prod.variants if v.size_label == "100ml Extrait"][0]
        assert v10.price == Decimal("499.00")
        assert v10.discounted_price == Decimal("399.00")
        assert v10.stock == 50
        prod_id = prod.id
        v10_id = v10.id
        v30_id = v30.id

    # 2. Verify storefront displays all 4 dynamic ML sizes
    storefront_res = auth_client.get(f"/products/{prod.slug}")
    assert storefront_res.status_code == 200
    assert b"10ml Travel Spray" in storefront_res.data
    assert b"30ml EDP" in storefront_res.data
    assert b"50ml EDP" in storefront_res.data
    assert b"100ml Extrait" in storefront_res.data

    # 3. Edit product:
    # - Modify 10ml to "15ml Pocket Spray"
    # - Delete 30ml variant
    # - Add a new 200ml Jumbo ML variant
    edit_res = auth_client.post(f"/admin/products/{prod_id}/edit", data={
        "name": "Oud Wood Royale",
        "slug": "oud-wood-royale",
        "category_ids": [str(cat_id)],
        "short_description": "Smoky exotic woods updated",
        "active": "1",
        f"var_label_{v10_id}": "15ml Pocket Spray",
        f"var_sku_{v10_id}": "OWR-15ML",
        f"var_price_{v10_id}": "599.00",
        f"var_discounted_price_{v10_id}": "499.00",
        f"var_stock_{v10_id}": "45",
        f"var_active_{v10_id}": "1",
        # Delete 30ml
        f"delete_var_{v30_id}": "1",
        # Add new variant
        "new_variant_label[]": ["200ml Flacon EDP"],
        "new_variant_sku[]": ["OWR-200ML"],
        "new_variant_price[]": ["4999.00"],
        "new_variant_discounted_price[]": ["4499.00"],
        "new_variant_stock[]": ["5"],
    }, follow_redirects=True)
    assert edit_res.status_code == 200

    with app.app_context():
        prod_updated = db.session.get(Product, prod_id)
        active_vars = prod_updated.active_variants
        active_labels = [v.size_label for v in active_vars]
        assert "15ml Pocket Spray" in active_labels
        assert "30ml EDP" not in active_labels
        assert "200ml Flacon EDP" in active_labels
        v200 = [v for v in active_vars if v.size_label == "200ml Flacon EDP"][0]
        assert v200.price == Decimal("4999.00")
        assert v200.stock == 5
