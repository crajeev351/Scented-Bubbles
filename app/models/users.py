from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    """Customer account model for Scented Bubbles registered shoppers."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(15), unique=True, nullable=True, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    customers = db.relationship("Customer", back_populates="user", lazy="dynamic")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def primary_customer(self):
        """Returns the primary linked Customer profile."""
        return self.customers.first()

    def get_orders(self, current_only=False):
        """Returns orders belonging to this user through linked customer profiles or matching phone.
        If current_only=True, returns ONLY active in-progress orders (excluding DELIVERED and CANCELLED).
        """
        from app.models.orders import Order
        from app.models.customers import Customer

        customer_ids = [c.id for c in self.customers.all()]
        if not customer_ids and not self.phone:
            return []

        query = Order.query
        conditions = []
        if customer_ids:
            conditions.append(Order.customer_id.in_(customer_ids))
        if self.phone:
            conditions.append(Order.shipping_phone == self.phone)

        from sqlalchemy import or_
        query = query.filter(or_(*conditions))

        if current_only:
            query = query.filter(Order.order_status.in_([
                Order.STATUS_PENDING,
                Order.STATUS_CONFIRMED,
                Order.STATUS_PACKED,
                Order.STATUS_SHIPPED,
            ]))

        return query.order_by(Order.created_at.desc()).all()

    def get_current_orders(self):
        """Returns ONLY currently active placed orders in transit/fulfillment (excludes old delivered orders)."""
        return self.get_orders(current_only=True)

    def __repr__(self):
        return f"<User {self.email or self.phone} ({self.name})>"
