from app.extensions import db


class ComboItem(db.Model):
    """Component variant line items that constitute a combo."""
    __tablename__ = "combo_items"

    id = db.Column(db.Integer, primary_key=True)
    combo_id = db.Column(db.Integer, db.ForeignKey("combos.id", ondelete="CASCADE"), nullable=False, index=True)
    product_variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = db.Column(db.Integer, default=1, nullable=False)

    combo = db.relationship("Combo", back_populates="items")
    variant = db.relationship("ProductVariant", lazy="selectin")

    def __repr__(self):
        return f"<ComboItem combo_id={self.combo_id} variant_id={self.product_variant_id} qty={self.quantity}>"
