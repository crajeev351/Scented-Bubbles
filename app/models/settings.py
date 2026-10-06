from datetime import datetime, timezone
from app.extensions import db


class Setting(db.Model):
    """Dynamic key-value configuration store for brand, store settings, and payment details."""
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @classmethod
    def get_value(cls, key: str, default: str = "") -> str:
        """Fetch setting value with optional default."""
        record = cls.query.filter_by(key=key).first()
        return record.value if record and record.value is not None else default

    @classmethod
    def get_all_dict(cls) -> dict:
        """Return all settings as a dictionary."""
        records = cls.query.all()
        return {item.key: item.value for item in records}

    @classmethod
    def set_value(cls, key: str, value: str, description: str = None):
        """Set or update setting value."""
        record = cls.query.filter_by(key=key).first()
        if record:
            record.value = str(value)
            if description:
                record.description = description
        else:
            record = cls(key=key, value=str(value), description=description)
            db.session.add(record)

    def __repr__(self):
        return f"<Setting {self.key}={self.value}>"
