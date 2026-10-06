from datetime import datetime, timezone
from app.extensions import db


class Category(db.Model):
    """Product category (e.g. Fine Fragrances, Car Perfumes, Discovery Sets)."""
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
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

    products = db.relationship(
        "Product",
        secondary="product_categories",
        back_populates="categories",
        lazy="dynamic",
    )

    @property
    def display_image_url(self) -> str:
        """Category card background image URL (medium size 800x450)."""
        if self.image_url:
            from app.services.image_service import get_image_url
            return get_image_url(self.image_url, size="medium")
        return ""

    def __repr__(self):
        return f"<Category {self.name}>"
