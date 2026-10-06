from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class Admin(db.Model):
    """Admin user table with lockout protection and two-factor authentication support."""
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Security Hardening Fields
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    totp_secret = db.Column(db.String(64), nullable=True)
    is_2fa_enabled = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_locked(self) -> bool:
        """Checks if the account is currently locked out due to failed attempts."""
        if self.locked_until:
            now = datetime.now(timezone.utc)
            locked_time = self.locked_until
            if locked_time.tzinfo is None:
                locked_time = locked_time.replace(tzinfo=timezone.utc)
            if locked_time > now:
                return True
            else:
                self.locked_until = None
                self.failed_login_attempts = 0
        return False

    def minutes_until_unlocked(self) -> int:
        """Returns the remaining lockout time in minutes."""
        if not self.is_locked():
            return 0
        now = datetime.now(timezone.utc)
        locked_time = self.locked_until
        if locked_time.tzinfo is None:
            locked_time = locked_time.replace(tzinfo=timezone.utc)
        diff = locked_time - now
        return max(1, int(diff.total_seconds() // 60) + 1)

    def record_failed_attempt(self, max_attempts: int = 5, lockout_minutes: int = 15):
        """Increments failed attempts and locks the account if threshold exceeded."""
        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)

    def record_successful_login(self):
        """Resets failed login attempts and clear any lockout."""
        self.failed_login_attempts = 0
        self.locked_until = None

    def __repr__(self):
        return f"<Admin {self.username}>"
