from datetime import datetime, timezone
from app.extensions import db


class OrderItem(db.Model):
    """Line item in an order. Crucially snapshots product details at order time."""
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_variant_id = db.Column(
        db.Integer,
        db.ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Snapshots to preserve order accuracy forever even if products or variants change
    product_name_snapshot = db.Column(db.String(150), nullable=False)
    variant_label_snapshot = db.Column(db.String(50), nullable=False)
    sku_snapshot = db.Column(db.String(64), nullable=False)
    unit_price_snapshot = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    order = db.relationship("Order", back_populates="items")
    variant = db.relationship("ProductVariant", lazy="selectin")

    def __repr__(self):
        return f"<OrderItem {self.product_name_snapshot} ({self.variant_label_snapshot}) x {self.quantity}>"
