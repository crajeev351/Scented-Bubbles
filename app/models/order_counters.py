from datetime import datetime, timezone
from app.extensions import db


class OrderCounter(db.Model):
    """Atomic daily counter for generating non-colliding order numbers (PERF-YYYYMMDD-NNNN)."""
    __tablename__ = "order_counters"

    id = db.Column(db.Integer, primary_key=True)
    date_str = db.Column(db.String(8), unique=True, nullable=False, index=True)  # YYYYMMDD
    last_seq = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self):
        return f"<OrderCounter {self.date_str}: {self.last_seq}>"
