import pytest
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models.categories import Category
from app.models.products import Product
from app.models.product_variants import ProductVariant
from app.models.settings import Setting
from app.services.cache_service import cache


@pytest.fixture
def app():
    """Create and configure a clean testing application instance."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # Default store settings
        Setting.set_value("company_name", "Scented Bubbles", "Brand name")
        Setting.set_value("delivery_charge", "50.00", "Delivery fee")
        Setting.set_value("free_delivery_threshold", "999.00", "Free delivery threshold")
        Setting.set_value("cod_enabled", "true", "COD enabled")
        Setting.set_value("support_whatsapp", "919876543210", "WhatsApp support")
        db.session.commit()
        cache.clear()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_catalog(app):
    """Creates a sample category, product with 2 variants for testing, returning safe IDs and metadata."""
    with app.app_context():
        cat = Category(name="Fine Fragrances", slug="fine-fragrances", active=True)
        db.session.add(cat)
        db.session.flush()

        prod = Product(
            category_id=cat.id,
            name="Velvet Oud Royal",
            slug="velvet-oud-royal",
            active=True,
            featured=True,
            bestseller=True,
        )
        db.session.add(prod)
        db.session.flush()

        v1 = ProductVariant(
            product_id=prod.id,
            size_label="50ml EDP",
            sku="VOR-50ML",
            price=Decimal("1499.00"),
            discounted_price=Decimal("1299.00"),
            stock=10,
            active=True,
        )
        v2 = ProductVariant(
            product_id=prod.id,
            size_label="100ml EDP",
            sku="VOR-100ML",
            price=Decimal("2499.00"),
            discounted_price=Decimal("2199.00"),
            stock=5,
            active=True,
        )
        db.session.add_all([v1, v2])
        db.session.commit()

        catalog_data = {
            "category_id": cat.id,
            "product_id": prod.id,
            "product_slug": prod.slug,
            "product_name": prod.name,
            "variant_50ml_id": v1.id,
            "variant_100ml_id": v2.id,
            "variant_50ml_sku": v1.sku,
            "variant_50ml_size": v1.size_label,
            "variant_50ml_stock": v1.stock,
            "variant_100ml_stock": v2.stock,
        }
        return catalog_data
