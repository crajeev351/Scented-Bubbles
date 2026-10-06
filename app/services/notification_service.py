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
            # 2. Send email notification if SMTP is configured
            NotificationService._send_email_notification(order, brand_name)
        except Exception as e:
            # Strictly catch all exceptions, log and proceed
            logger.exception(f"Notification dispatch failed for order {order.order_id}: {e}")

    @staticmethod
    def _send_email_notification(order, brand_name: str):
        """Sends new order notification to the store owner via SMTP if configured."""
        try:
            cfg = current_app.config
            smtp_host = cfg.get("SMTP_HOST")
            smtp_user = cfg.get("SMTP_USER")
            smtp_pass = cfg.get("SMTP_PASSWORD")
            to_email = cfg.get("NOTIFICATION_EMAIL")

            if not (smtp_host and smtp_user and smtp_pass and to_email):
                logger.debug("SMTP not configured; skipping email notification.")
                return

            msg = MIMEMultipart()
            msg["Subject"] = f"[{brand_name}] New Order #{order.order_id} Received (₹{order.total_amount})"
            msg["From"] = smtp_user
            msg["To"] = to_email

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
            msg.attach(MIMEText(body, "plain"))

            port = cfg.get("SMTP_PORT", 587)
            server = smtplib.SMTP(smtp_host, port, timeout=10)
            if cfg.get("SMTP_USE_TLS", True):
                server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            logger.info(f"Order notification email sent for {order.order_id}")
        except Exception as e:
            logger.warning(f"Failed to send email notification for order {order.order_id}: {e}")
