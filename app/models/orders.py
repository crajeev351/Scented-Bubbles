from datetime import datetime, timezone
from app.extensions import db


class Order(db.Model):
    """Customer order entity with atomic ID, idempotency token, and financial decimals."""
    __tablename__ = "orders"

    # Status State Machines
    STATUS_PENDING = "PENDING"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_PACKED = "PACKED"
    STATUS_SHIPPED = "SHIPPED"
    STATUS_DELIVERED = "DELIVERED"
    STATUS_CANCELLED = "CANCELLED"
    ORDER_STATUSES = [
        STATUS_PENDING,
        STATUS_CONFIRMED,
        STATUS_PACKED,
        STATUS_SHIPPED,
        STATUS_DELIVERED,
        STATUS_CANCELLED,
    ]

    PAYMENT_PENDING_VERIFICATION = "PENDING_VERIFICATION"
    PAYMENT_PAID = "PAID"
    PAYMENT_FAILED = "FAILED"
    PAYMENT_REFUNDED = "REFUNDED"
    PAYMENT_STATUSES = [
        PAYMENT_PENDING_VERIFICATION,
        PAYMENT_PAID,
        PAYMENT_FAILED,
        PAYMENT_REFUNDED,
    ]

    id = db.Column(db.Integer, primary_key=True)
    # Human-readable atomic ID e.g. PERF-20260930-0001
    order_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    idempotency_token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    
    # Financial fields in Decimal
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    delivery_charge = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)

    order_status = db.Column(db.String(24), default=STATUS_PENDING, nullable=False, index=True)
    payment_status = db.Column(db.String(24), default=PAYMENT_PENDING_VERIFICATION, nullable=False, index=True)
    payment_method = db.Column(db.String(32), nullable=False)  # "MANUAL_UPI" or "COD"

    # Shipping Address Snapshot
    shipping_name = db.Column(db.String(100), nullable=False)
    shipping_phone = db.Column(db.String(15), nullable=False)
    shipping_address_line1 = db.Column(db.String(255), nullable=False)
    shipping_address_line2 = db.Column(db.String(255), nullable=True)
    shipping_city = db.Column(db.String(100), nullable=False)
    shipping_state = db.Column(db.String(100), nullable=False)
    shipping_pincode = db.Column(db.String(10), nullable=False)
    notes = db.Column(db.Text, nullable=True)

    # Fulfillment Milestones & Exact Timestamps
    payment_verified_at = db.Column(db.DateTime, nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    packed_at = db.Column(db.DateTime, nullable=True)
    shipped_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    # Courier Tracking Details
    courier_name = db.Column(db.String(100), nullable=True)
    tracking_number = db.Column(db.String(100), nullable=True)
    tracking_url = db.Column(db.String(255), nullable=True)
    cancellation_reason = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    customer = db.relationship("Customer", back_populates="orders")
    items = db.relationship(
        "OrderItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    payments = db.relationship(
        "Payment",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    status_history = db.relationship(
        "OrderStatusHistory",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at.asc()",
    )

    @property
    def latest_payment(self):
        """Returns the most recent payment record."""
        return self.payments[-1] if self.payments else None

    @property
    def is_cancellable(self) -> bool:
        """Orders can be cancelled before packing/shipping."""
        return self.order_status in (self.STATUS_PENDING, self.STATUS_CONFIRMED)

    # IST Convenience Properties
    @property
    def created_at_ist(self):
        from app.utils.timezone import to_ist
        return to_ist(self.created_at)

    @property
    def confirmed_at_ist(self):
        from app.utils.timezone import to_ist
        return to_ist(self.confirmed_at)

    @property
    def packed_at_ist(self):
        from app.utils.timezone import to_ist
        return to_ist(self.packed_at)

    @property
    def shipped_at_ist(self):
        from app.utils.timezone import to_ist
        return to_ist(self.shipped_at)

    @property
    def delivered_at_ist(self):
        from app.utils.timezone import to_ist
        return to_ist(self.delivered_at)

    @property
    def cancelled_at_ist(self):
        from app.utils.timezone import to_ist
        return to_ist(self.cancelled_at)

    def __repr__(self):
        return f"<Order {self.order_id} ({self.order_status}, ₹{self.total_amount})>"
