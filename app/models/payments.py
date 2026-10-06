from datetime import datetime, timezone
from app.extensions import db


class Payment(db.Model):
    """Payment record linked to orders. Enforces unique UTR constraint for manual UPI."""
    __tablename__ = "payments"

    METHOD_MANUAL_UPI = "MANUAL_UPI"
    METHOD_COD = "COD"
    METHOD_RAZORPAY = "RAZORPAY"

    STATUS_PENDING_VERIFICATION = "PENDING_VERIFICATION"
    STATUS_PAID = "PAID"
    STATUS_FAILED = "FAILED"
    STATUS_REFUNDED = "REFUNDED"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_method = db.Column(db.String(32), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Crucial unique constraint on UTR to prevent duplicate transaction reuse
    utr = db.Column(db.String(64), unique=True, nullable=True, index=True)
    status = db.Column(db.String(32), default=STATUS_PENDING_VERIFICATION, nullable=False, index=True)
    
    notes = db.Column(db.Text, nullable=True)
    raw_response = db.Column(db.Text, nullable=True)  # JSON or transaction audit trail

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    order = db.relationship("Order", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.id} method={self.payment_method} utr={self.utr} status={self.status}>"
