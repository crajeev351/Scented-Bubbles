from datetime import datetime, timezone
from app.extensions import db


class ProductImage(db.Model):
    """Product images with relative storage keys."""
    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    image_key = db.Column(db.String(255), nullable=False)  # Relative key in storage
    alt_text = db.Column(db.String(255), nullable=True)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    product = db.relationship("Product", back_populates="images")

    @property
    def image_url(self) -> str:
        """Resolve medium URL using image service (defaults to /static/uploads/... or custom CDN)."""
        from app.services.image_service import get_image_url
        return get_image_url(self.image_key, size="medium")

    @property
    def thumbnail_url(self) -> str:
        """Resolve thumb size URL (sub-150KB, max 400px)."""
        from app.services.image_service import get_image_url
        return get_image_url(self.image_key, size="thumb")

    @property
    def large_url(self) -> str:
        """Resolve large size URL (max 1200px)."""
        from app.services.image_service import get_image_url
        return get_image_url(self.image_key, size="large")

    @property
    def srcset(self) -> str:
        """Standard responsive HTML srcset."""
        from app.services.image_service import get_image_srcset
        return get_image_srcset(self.image_key)

    def __repr__(self):
        return f"<ProductImage {self.id} (key={self.image_key})>"
