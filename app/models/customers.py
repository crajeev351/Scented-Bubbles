from datetime import datetime, timezone
from app.extensions import db


class Customer(db.Model):
    """Customer profile matched or created primarily by phone number during guest checkout."""
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(15), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True, index=True)
    address_line1 = db.Column(db.String(255), nullable=True)
    address_line2 = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    pincode = db.Column(db.String(10), nullable=True)
    
    # Optional link to user account if customer registers in future
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user = db.relationship("User", back_populates="customers")

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    orders = db.relationship("Order", back_populates="customer", lazy="dynamic")

    def __repr__(self):
        return f"<Customer {self.phone} ({self.name})>"
