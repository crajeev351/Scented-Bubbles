from datetime import datetime, timezone
from app.extensions import db


# Association table for product <-> category many-to-many relationship
product_categories = db.Table(
    "product_categories",
    db.Column("product_id", db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class Product(db.Model):
    """Product model for perfumes and car perfumes."""
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True, index=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    short_description = db.Column(db.String(255), nullable=True)
    full_description = db.Column(db.Text, nullable=True)
    
    # Fragrance specific characteristics: inspired designer clone & olfactory notes
    inspired_by = db.Column(db.String(150), nullable=True, index=True)  # e.g. "Gucci Flora", "Baccarat Rouge 540"
    fragrance_family = db.Column(db.String(80), nullable=True)  # Legacy fallback / aroma category
    top_notes = db.Column(db.String(255), nullable=True)
    heart_notes = db.Column(db.String(255), nullable=True)
    base_notes = db.Column(db.String(255), nullable=True)
    usage_instructions = db.Column(db.Text, nullable=True)

    active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    featured = db.Column(db.Boolean, default=False, nullable=False, index=True)
    bestseller = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    category = db.relationship("Category", foreign_keys=[category_id])
    categories = db.relationship(
        "Category",
        secondary=product_categories,
        back_populates="products",
        lazy="selectin",
    )
    variants = db.relationship(
        "ProductVariant",
        back_populates="product",
        lazy="selectin",
        order_by="ProductVariant.display_order",
        cascade="all, delete-orphan",
    )
    images = db.relationship(
        "ProductImage",
        back_populates="product",
        lazy="selectin",
        order_by="ProductImage.display_order",
        cascade="all, delete-orphan",
    )

    @property
    def primary_image(self):
        """Returns primary product image or the first available image."""
        for img in self.images:
            if img.is_primary:
                return img
        return self.images[0] if self.images else None

    @property
    def primary_image_url(self):
        img = self.primary_image
        return img.image_url if img else "/static/images/placeholder_perfume.webp"

    @property
    def thumbnail_url(self):
        """Card thumbnail URL (max 400px, sub-150KB)."""
        img = self.primary_image
        return img.thumbnail_url if img else "/static/images/placeholder_perfume.webp"

    @property
    def primary_image_srcset(self):
        img = self.primary_image
        return img.srcset if img else ""

    @property
    def active_variants(self):
        """Active and non-deleted variants."""
        return [v for v in self.variants if v.active and not v.is_deleted]

    @property
    def default_variant(self):
        """Default selected variant (first active with stock, or first active)."""
        active_vars = self.active_variants
        for v in active_vars:
            if v.stock > 0:
                return v
        return active_vars[0] if active_vars else None

    @property
    def in_stock(self) -> bool:
        """True if at least one active variant has remaining stock."""
        return any(v.stock > 0 for v in self.active_variants)

    @property
    def is_low_stock(self) -> bool:
        """True if in stock and default variant has low stock (1 to 5 units)."""
        if not self.in_stock:
            return False
        dv = self.default_variant
        return bool(dv and dv.is_low_stock)

    @property
    def min_price(self):
        active_vars = self.active_variants
        if not active_vars:
            return 0
        return min(v.effective_price for v in active_vars)

    @property
    def max_price(self):
        active_vars = self.active_variants
        if not active_vars:
            return 0
        return max(v.effective_price for v in active_vars)

    def __repr__(self):
        return f"<Product {self.name} (slug={self.slug})>"


@db.event.listens_for(db.session, "before_flush")
def sync_product_categories(session, flush_context, instances):
    for obj in session.new:
        if isinstance(obj, Product):
            if obj.categories and not obj.category_id:
                obj.category_id = obj.categories[0].id
            elif obj.category_id and not obj.categories:
                from app.models.categories import Category
                cat = session.get(Category, obj.category_id)
                if cat and cat not in obj.categories:
                    obj.categories.append(cat)
    for obj in session.dirty:
        if isinstance(obj, Product):
            if obj.categories and (not obj.category_id or obj.category_id not in [c.id for c in obj.categories]):
                obj.category_id = obj.categories[0].id
            elif obj.category_id and not obj.categories:
                from app.models.categories import Category
                cat = session.get(Category, obj.category_id)
                if cat and cat not in obj.categories:
                    obj.categories.append(cat)
