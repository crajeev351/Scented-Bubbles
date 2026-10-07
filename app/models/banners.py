from datetime import datetime, timezone
from app.extensions import db


class Banner(db.Model):
    """Hero banners and promotional sliders on the homepage."""
    __tablename__ = "banners"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    subtitle = db.Column(db.String(255), nullable=True)
    link_url = db.Column(db.String(255), nullable=True)
    image_key = db.Column(db.String(255), nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Custom promotional banner fields (The Man Company style)
    tagline = db.Column(db.String(150), nullable=True)  # e.g. "WHAT'S YOUR MOOD TODAY?"
    button_text = db.Column(db.String(80), nullable=True, default="SHOP NOW")  # e.g. "SHOP NOW", "BUY NOW @ ₹335"
    secondary_button_text = db.Column(db.String(80), nullable=True)  # Optional second button label
    secondary_button_link = db.Column(db.String(255), nullable=True)
    target_type = db.Column(db.String(30), nullable=True, default="custom")  # 'product', 'combo', 'category', 'custom'
    overlay_opacity = db.Column(db.Integer, default=55, nullable=True)  # Darkness %: 20-90
    image_mobile_key = db.Column(db.String(255), nullable=True)  # Optional mobile-specific background image (800x800 or 750x900)

    @property
    def image_mobile_url(self) -> str:
        """Returns dedicated mobile banner URL (max 800px) or falls back to desktop image_url."""
        if self.image_mobile_key:
            from app.services.image_service import get_image_url
            return get_image_url(self.image_mobile_key, size="large")
        return self.image_url

    @property
    def thumbnail_mobile_url(self) -> str:
        """Returns thumbnail for mobile banner in admin."""
        if self.image_mobile_key:
            from app.services.image_service import get_image_url
            return get_image_url(self.image_mobile_key, size="thumb")
        return ""

    @property
    def has_mobile_image(self) -> bool:
        return bool(self.image_mobile_key)

    @property
    def display_button_text(self) -> str:
        """Returns button label, defaulting to 'SHOP NOW'."""
        return self.button_text.strip() if self.button_text and self.button_text.strip() else "SHOP NOW"

    @property
    def resolved_link_url(self) -> str:
        """Dynamically computes the destination URL based on selected product, combo, category, or custom URL."""
        if self.target_type == "product" and self.target_id:
            from app.models.products import Product
            prod = db.session.get(Product, self.target_id)
            if prod:
                return f"/products/{prod.slug}"
        elif self.target_type == "combo" and self.target_id:
            from app.models.combos import Combo
            cmb = db.session.get(Combo, self.target_id)
            if cmb:
                return f"/combos/{cmb.slug}"
        elif self.target_type == "category" and self.target_id:
            from app.models.categories import Category
            cat = db.session.get(Category, self.target_id)
            if cat:
                return f"/categories/{cat.slug}"

        return self.link_url.strip() if self.link_url and self.link_url.strip() else "/products"

    @property
    def target_object(self):
        """Returns the targeted entity instance (Product, Combo, or Category) if linked."""
        if self.target_type == "product" and self.target_id:
            from app.models.products import Product
            return db.session.get(Product, self.target_id)
        elif self.target_type == "combo" and self.target_id:
            from app.models.combos import Combo
            return db.session.get(Combo, self.target_id)
        elif self.target_type == "category" and self.target_id:
            from app.models.categories import Category
            return db.session.get(Category, self.target_id)
        return None

    @property
    def image_url(self) -> str:
        """Banner large size URL (max 1200px)."""
        if self.image_key:
            from app.services.image_service import get_image_url
            return get_image_url(self.image_key, size="large")
        return "/static/images/placeholder_banner.webp"

    @property
    def thumbnail_url(self) -> str:
        """Banner thumbnail for admin lists."""
        if self.image_key:
            from app.services.image_service import get_image_url
            return get_image_url(self.image_key, size="thumb")
        return "/static/images/placeholder_banner.webp"

    @property
    def image_srcset(self) -> str:
        if self.image_key:
            from app.services.image_service import get_image_srcset
            return get_image_srcset(self.image_key)
        return ""

    def __repr__(self):
        return f"<Banner {self.title}>"
