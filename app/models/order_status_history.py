from datetime import datetime, timezone
from app.extensions import db


class OrderStatusHistory(db.Model):
    """Audit log of order milestone status changes with exact timestamps."""
    __tablename__ = "order_status_history"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.String(64), default="System", nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    order = db.relationship("Order", back_populates="status_history")

    @property
    def created_at_ist(self):
        from app.utils.timezone import to_ist
        return to_ist(self.created_at)

    def __repr__(self):
        return f"<OrderStatusHistory {self.order_id} {self.status} at {self.created_at}>"
