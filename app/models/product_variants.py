from datetime import datetime, timezone
from decimal import Decimal
from app.extensions import db


class ProductVariant(db.Model):
    """Size / volume variant for a product (e.g. 10ml, 30ml, 50ml, 100ml, Car Diffuser)."""
    __tablename__ = "product_variants"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    size_label = db.Column(db.String(50), nullable=False)  # e.g., "50ml", "100ml", "Diffuser Pod"
    sku = db.Column(db.String(64), unique=True, nullable=False, index=True)
    
    # Financial precision with Decimal / Numeric(10, 2)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    discounted_price = db.Column(db.Numeric(10, 2), nullable=True)
    
    stock = db.Column(db.Integer, default=0, nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    product = db.relationship("Product", back_populates="variants")

    @property
    def effective_price(self) -> Decimal:
        """Returns discounted_price if set and strictly lower than regular price, else regular price."""
        if self.discounted_price is not None and self.discounted_price > 0 and self.discounted_price < self.price:
            return Decimal(str(self.discounted_price))
        return Decimal(str(self.price))

    @property
    def discount_percentage(self) -> int:
        """Derived discount percentage; never stored in DB."""
        if self.discounted_price is not None and self.discounted_price > 0 and self.discounted_price < self.price:
            diff = self.price - self.discounted_price
            pct = (diff / self.price) * 100
            return int(round(pct))
        return 0

    @property
    def in_stock(self) -> bool:
        return bool(self.stock > 0 and self.active and not self.is_deleted)

    @property
    def is_low_stock(self) -> bool:
        """True if stock is strictly between 1 and 5 inclusive."""
        return bool(self.stock > 0 and self.stock <= 5 and self.active and not self.is_deleted)

    def __repr__(self):
        return f"<ProductVariant {self.sku} ({self.size_label}) - Stock: {self.stock}>"
