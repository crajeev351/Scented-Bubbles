from datetime import datetime, timezone
from decimal import Decimal
from app.extensions import db


class Combo(db.Model):
    """Curated fragrance combo packs (e.g. Day & Night Duo, Car & Home Kit)."""
    __tablename__ = "combos"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    short_description = db.Column(db.String(255), nullable=True)
    full_description = db.Column(db.Text, nullable=True)
    combo_price = db.Column(db.Numeric(10, 2), nullable=False)
    image_key = db.Column(db.String(255), nullable=True)
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

    items = db.relationship(
        "ComboItem",
        back_populates="combo",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    @property
    def image_url(self) -> str:
        if self.image_key:
            from app.services.image_service import get_image_url
            return get_image_url(self.image_key, size="medium")
        return "/static/images/placeholder_combo.webp"

    @property
    def thumbnail_url(self) -> str:
        if self.image_key:
            from app.services.image_service import get_image_url
            return get_image_url(self.image_key, size="thumb")
        return "/static/images/placeholder_combo.webp"

    @property
    def image_srcset(self) -> str:
        if self.image_key:
            from app.services.image_service import get_image_srcset
            return get_image_srcset(self.image_key)
        return ""

    @property
    def original_price(self) -> Decimal:
        """Sum of component variants' individual effective prices."""
        total = Decimal("0.00")
        for item in self.items:
            if item.variant:
                total += item.variant.effective_price * item.quantity
        return total

    @property
    def savings(self) -> Decimal:
        """Derived monetary savings between sum of items and combo price."""
        orig = self.original_price
        if orig > self.combo_price:
            return orig - self.combo_price
        return Decimal("0.00")

    @property
    def in_stock(self) -> bool:
        """Stock rule: combo availability is derived strictly from component stocks."""
        if not self.items:
            return False
        return all(
            item.variant and item.variant.stock >= item.quantity and item.variant.active and not item.variant.is_deleted
            for item in self.items
        )

    @property
    def max_available(self) -> int:
        """Maximum number of combos that can be fulfilled with currently available component stock."""
        if not self.items:
            return 0
        counts = []
        for item in self.items:
            if not item.variant or not item.variant.active or item.variant.is_deleted or item.variant.stock < item.quantity:
                return 0
            counts.append(item.variant.stock // item.quantity)
        return min(counts) if counts else 0

    def __repr__(self):
        return f"<Combo {self.name} - Price: {self.combo_price}>"
