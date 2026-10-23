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

    @property
    def confirmed_orders(self):
        """Dynamic query for confirmed orders only (matching admin orders panel)."""
        from app.models.orders import Order
        return self.orders.filter(Order.is_confirmed.is_(True))

    @property
    def confirmed_orders_count(self) -> int:
        """Count of confirmed orders where payment has been submitted/processed."""
        if hasattr(self, "_confirmed_orders_count") and self._confirmed_orders_count is not None:
            return self._confirmed_orders_count
        from app.models.orders import Order
        return self.orders.filter(Order.is_confirmed.is_(True)).count()

    @property
    def orders_count(self) -> int:
        """Alias for confirmed_orders_count matching the admin orders section."""
        return self.confirmed_orders_count

    @property
    def time_since_joined(self) -> str:
        """Returns a human-readable relative duration string (e.g. '2 days ago', '3 weeks ago')."""
        if not self.created_at:
            return ""
        now = datetime.now(timezone.utc)
        dt = self.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = now - dt
        seconds = max(0, int(delta.total_seconds()))
        if seconds < 60:
            return "Just now"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        days = delta.days
        if days == 1:
            return "1 day ago"
        if days < 7:
            return f"{days} days ago"
        weeks = days // 7
        if weeks < 5:
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        months = days // 30
        if months < 12:
            return f"{months} month{'s' if months > 1 else ''} ago"
        years = days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"

    def __repr__(self):
        return f"<Customer {self.phone} ({self.name})>"

