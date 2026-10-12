import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

logger = logging.getLogger(__name__)


class NotificationService:
    """Orchestrates notifications for new orders across admin badge, email, and WhatsApp."""

    @staticmethod
    def notify_order_created(order, brand_name: str = "Scented Bubbles"):
        """Dispatches notifications. CRITICAL: Notification failure must NEVER fail or roll back an order."""
        try:
            # 1. Admin badge: automatically reflected in DB queries (order_status == PENDING)
            # 2. Send email notification to store owner if SMTP is configured
            NotificationService._send_email_notification(order, brand_name)
            # 3. Send customer order confirmation email if customer provided an email address
            NotificationService.send_customer_order_confirmation(order, brand_name)
        except Exception as e:
            # Strictly catch all exceptions, log and proceed
            logger.exception(f"Notification dispatch failed for order {order.order_id}: {e}")

    @staticmethod
    def get_smtp_config():
        """Retrieves active SMTP configuration from database Setting, with fallback to environment."""
        from app.models.settings import Setting
        db_s = Setting.get_all_dict()
        cfg = current_app.config

        host = db_s.get("smtp_host") or cfg.get("SMTP_HOST") or "smtp.gmail.com"
        port_raw = db_s.get("smtp_port") or cfg.get("SMTP_PORT") or 587
        try:
            port = int(port_raw)
        except (ValueError, TypeError):
            port = 587

        user = db_s.get("smtp_user") or cfg.get("SMTP_USER") or ""
        password = db_s.get("smtp_password") or cfg.get("SMTP_PASSWORD") or ""
        use_tls_raw = db_s.get("smtp_use_tls")
        if use_tls_raw is not None and str(use_tls_raw).strip() != "":
            use_tls = str(use_tls_raw).lower() in ("true", "1", "yes")
        else:
            use_tls = cfg.get("SMTP_USE_TLS", True)

        notification_email = db_s.get("notification_email") or cfg.get("NOTIFICATION_EMAIL") or user

        return {
            "host": host.strip(),
            "port": port,
            "user": user.strip(),
            "password": password.strip(),
            "use_tls": use_tls,
            "notification_email": notification_email.strip() if notification_email else "",
        }

    @staticmethod
    def test_smtp_connection(test_recipient: str = None) -> tuple[bool, str]:
        """Tests SMTP credentials and optionally sends a verification email."""
        try:
            smtp_cfg = NotificationService.get_smtp_config()
            smtp_host = smtp_cfg["host"]
            smtp_user = smtp_cfg["user"]
            smtp_pass = smtp_cfg["password"]
            port = smtp_cfg["port"]
            use_tls = smtp_cfg["use_tls"]
            target = test_recipient or smtp_cfg["notification_email"] or smtp_user

            if not (smtp_host and smtp_user and smtp_pass):
                return False, "SMTP Host, Username, and Password must be filled."

            server = smtplib.SMTP(smtp_host, port, timeout=10)
            if use_tls:
                server.starttls()
            server.login(smtp_user, smtp_pass)

            if target:
                brand_name = "Scented Bubbles"
                msg = MIMEMultipart()
                msg["Subject"] = f"[{brand_name}] SMTP Test Email — Verified Successfully! ✅"
                msg["From"] = smtp_user
                msg["To"] = target
                msg.attach(MIMEText(
                    f"Congratulations!\n\n"
                    f"Your SMTP email configuration for {brand_name} is active and working properly.\n"
                    f"Customer password resets and new order notifications will now be delivered reliably.\n\n"
                    f"Sent via: {smtp_host}:{port} ({smtp_user})",
                    "plain"
                ))
                server.send_message(msg)

            server.quit()
            return True, f"SMTP verified successfully! Test email delivered to {target}."
        except Exception as e:
            logger.exception("SMTP test probe failed")
            return False, f"SMTP connection failed: {str(e)}"

    @staticmethod
    def _send_smtp_message(to_email: str, subject: str, body_text: str):
        """Low-level helper to send an SMTP email using dynamic app configuration."""
        try:
            smtp_cfg = NotificationService.get_smtp_config()
            smtp_host = smtp_cfg["host"]
            smtp_user = smtp_cfg["user"]
            smtp_pass = smtp_cfg["password"]
            port = smtp_cfg["port"]
            use_tls = smtp_cfg["use_tls"]

            if not (smtp_host and smtp_user and smtp_pass and to_email):
                logger.debug(f"SMTP not configured or recipient empty; skipping email to {to_email}.")
                return False

            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = to_email
            msg.attach(MIMEText(body_text, "plain"))

            server = smtplib.SMTP(smtp_host, port, timeout=10)
            if use_tls:
                server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            logger.warning(f"SMTP send failed to {to_email}: {e}")
            return False

    @staticmethod
    def _send_email_notification(order, brand_name: str):
        """Sends new order notification to the store owner via SMTP if configured."""
        try:
            smtp_cfg = NotificationService.get_smtp_config()
            to_email = smtp_cfg.get("notification_email")
            if not to_email:
                return

            subject = f"[{brand_name}] New Order #{order.order_id} Received (₹{order.total_amount})"
            body = (
                f"New Order Received at {brand_name}!\n\n"
                f"Order ID: {order.order_id}\n"
                f"Customer: {order.shipping_name} ({order.shipping_phone})\n"
                f"Total Amount: ₹{order.total_amount}\n"
                f"Payment Method: {order.payment_method} ({order.payment_status})\n"
                f"Shipping Address:\n"
                f"{order.shipping_address_line1}, {order.shipping_city}, {order.shipping_state} - {order.shipping_pincode}\n\n"
                f"Review order in your admin dashboard."
            )
            if NotificationService._send_smtp_message(to_email, subject, body):
                logger.info(f"Store owner notification email sent for order {order.order_id}")
        except Exception as e:
            logger.warning(f"Failed to send owner notification email for {order.order_id}: {e}")

    @staticmethod
    def send_customer_order_confirmation(order, brand_name: str = "Scented Bubbles"):
        """Sends order confirmation receipt to customer if customer email was provided."""
        try:
            customer_email = order.shipping_email or (order.customer.email if order.customer else None)
            if not customer_email:
                return

            subject = f"Your Order Confirmation #{order.order_id} - {brand_name}"
            body = (
                f"Hello {order.shipping_name},\n\n"
                f"Thank you for shopping with {brand_name}! We have received your order.\n\n"
                f"Order ID: {order.order_id}\n"
                f"Total: ₹{order.total_amount}\n"
                f"Payment Method: {order.payment_method}\n"
                f"Shipping Address:\n"
                f"{order.shipping_address_line1}, {order.shipping_city}, {order.shipping_state} - {order.shipping_pincode}\n\n"
                f"You can track your order status anytime through your account.\n\n"
                f"Warm regards,\n"
                f"{brand_name} Team"
            )
            if NotificationService._send_smtp_message(customer_email, subject, body):
                logger.info(f"Customer confirmation email sent to {customer_email} for order {order.order_id}")
        except Exception as e:
            logger.warning(f"Failed to send customer order confirmation email: {e}")

    @staticmethod
    def send_password_reset_email(to_email: str, reset_url: str, brand_name: str = "Scented Bubbles"):
        """Sends secure password reset link to customer."""
        try:
            subject = f"Reset Your Password - {brand_name}"
            body = (
                f"Hello,\n\n"
                f"We received a request to reset the password for your {brand_name} account.\n\n"
                f"Click the link below (or copy and paste it into your browser) to set a new password:\n"
                f"{reset_url}\n\n"
                f"This password reset link will expire in 60 minutes.\n"
                f"If you did not request a password reset, you can safely ignore this email.\n\n"
                f"Best,\n"
                f"The {brand_name} Team"
            )
            return NotificationService._send_smtp_message(to_email, subject, body)
        except Exception as e:
            logger.warning(f"Failed to send password reset email to {to_email}: {e}")
            return False

