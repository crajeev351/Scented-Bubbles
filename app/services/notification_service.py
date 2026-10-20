import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

logger = logging.getLogger(__name__)


class NotificationService:
    """Orchestrates notifications for new orders across admin badge, email, and WhatsApp."""

    @staticmethod
    def get_customer_email(order) -> str:
        """Safely extracts and validates the customer's registered email address."""
        if not order:
            return ""

        email = None
        # 1. From linked customer profile
        if getattr(order, "customer", None):
            if order.customer.email:
                email = str(order.customer.email).strip()
            elif getattr(order.customer, "user", None) and order.customer.user.email:
                email = str(order.customer.user.email).strip()

        # 2. From database query if relationship is detached or not loaded
        if not email and getattr(order, "customer_id", None):
            try:
                from app.models.customers import Customer
                from app.extensions import db
                cust = db.session.get(Customer, order.customer_id)
                if cust:
                    if cust.email:
                        email = str(cust.email).strip()
                    elif getattr(cust, "user", None) and cust.user.email:
                        email = str(cust.user.email).strip()
            except Exception:
                pass

        if email and "@" in email and "." in email:
            return email.lower()
        return ""

    @staticmethod
    def notify_order_created(order, brand_name: str = "Scented Bubbles", async_mode: bool = True):
        """Dispatches notifications. Asynchronous by default in web requests so HTTP redirect is instantaneous."""
        try:
            # 1. Deduplication Guard: Never send order notifications more than once for the same order
            if getattr(order, "notification_sent", False):
                logger.info(f"Order notification already dispatched for {order.order_id}; skipping duplicate dispatch.")
                return

            # Mark notification_sent upfront and commit to database to eliminate race conditions
            order.notification_sent = True
            from app.extensions import db
            db.session.commit()

            # 2. Testing Mode Check: Store owner can mute order notifications in Admin Settings while testing
            from app.models.settings import Setting
            order_notifs_enabled = Setting.get_value("order_notifications_enabled", "true")
            if str(order_notifs_enabled).strip().lower() in ("false", "0", "no", "disabled"):
                logger.info(f"Order notification emails are muted in Store Settings (Testing Mode). Skipping email for order {order.order_id}.")
                return

            # In unit testing / pytest mode, execute synchronously so test assertions succeed immediately
            is_testing = current_app and current_app.config.get("TESTING")
            if is_testing or not async_mode:
                NotificationService._execute_notification_send(order, brand_name)
                return

            # In production web requests, dispatch in a non-blocking background daemon thread
            import threading
            app = current_app._get_current_object()
            order_id = order.id
            thread = threading.Thread(
                target=NotificationService._async_notification_worker,
                args=(app, order_id, brand_name),
                daemon=True,
                name=f"OrderNotif-{order.order_id}",
            )
            thread.start()
            logger.info(f"Spawned background notification worker for order #{order.order_id}")

        except Exception as e:
            # Strictly catch all exceptions, log and proceed
            logger.exception(f"Notification dispatch failed for order {order.order_id}: {e}")

    @staticmethod
    def _async_notification_worker(app, order_id: int, brand_name: str):
        """Background worker thread executing email deliveries with full application context."""
        with app.app_context():
            try:
                from app.models.orders import Order
                from app.extensions import db
                order = db.session.get(Order, order_id)
                if not order:
                    logger.warning(f"Async notification worker could not find order ID {order_id}")
                    return

                NotificationService._execute_notification_send(order, brand_name)

            except Exception as e:
                logger.exception(f"Background notification worker encountered error for order ID {order_id}: {e}")

    @staticmethod
    def _execute_notification_send(order, brand_name: str):
        """Executes the email deliveries: sends new order alert to store owner only (customer emails skipped)."""
        try:
            # 1. Send store owner alert email ONLY
            NotificationService._send_email_notification(order, brand_name)

            # 2. Customer emails skipped per store owner preference
            from app.models.settings import Setting
            if str(Setting.get_value("customer_emails_enabled", "false")).strip().lower() in ("true", "1", "yes"):
                customer_email = NotificationService.get_customer_email(order)
                if customer_email:
                    NotificationService.send_customer_order_confirmation(order, brand_name, customer_email=customer_email)
            else:
                logger.info(f"Order #{order.order_id}: Customer emails are disabled; only store owner notified.")

        except Exception as e:
            logger.exception(f"Error executing email send for order #{order.order_id}: {e}")

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
    def _send_brevo_message(api_key: str, to_email: str, subject: str, body_text: str, html_body: str = None) -> bool:
        """Sends email via Brevo (Sendinblue) HTTPS API (Port 443). 100% bypasses Render Free SMTP blocks."""
        try:
            import requests
            from app.models.settings import Setting
            brand_name = Setting.get_value("company_name", "Scented Bubbles")
            sender_email = Setting.get_value("smtp_user", "crajeev351@gmail.com")

            payload = {
                "sender": {"name": brand_name, "email": sender_email},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_body if html_body else f"<p>{body_text}</p>",
                "textContent": body_text,
            }
            resp = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": api_key.strip(),
                    "content-type": "application/json",
                    "accept": "application/json",
                },
                json=payload,
                timeout=12,
            )
            if resp.status_code in (200, 201, 202):
                msg_id = resp.json().get("messageId", "")
                logger.info(f"Email successfully delivered via Brevo HTTPS API to {to_email} (MsgID: {msg_id})")
                return True
            else:
                logger.warning(f"Brevo API error ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            logger.warning(f"Brevo API request failed to {to_email}: {e}")
            return False

    @staticmethod
    def _send_resend_message(api_key: str, to_email: str, subject: str, body_text: str, html_body: str = None) -> bool:
        """Sends email via Resend HTTPS API (Port 443). 100% bypasses Render Free SMTP blocks."""
        try:
            import requests
            from app.models.settings import Setting
            brand_name = Setting.get_value("company_name", "Scented Bubbles")
            from_sender = Setting.get_value("resend_from_email") or f"{brand_name} <onboarding@resend.dev>"

            payload = {
                "from": from_sender,
                "to": [to_email],
                "subject": subject,
                "html": html_body if html_body else f"<p>{body_text}</p>",
                "text": body_text,
            }
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=12,
            )
            if resp.status_code in (200, 201, 202):
                res_id = resp.json().get("id", "")
                logger.info(f"Email successfully delivered via Resend HTTPS API to {to_email} (ID: {res_id})")
                return True
            else:
                logger.warning(f"Resend API error ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            logger.warning(f"Resend API request failed to {to_email}: {e}")
            return False

    @staticmethod
    def test_smtp_connection(test_recipient: str = None) -> tuple[bool, str]:
        """Tests active email dispatch method (Brevo HTTPS API, Resend HTTPS API, or SMTP) and sends a verification email."""
        try:
            if current_app and current_app.config.get("TESTING"):
                return True, "Email test simulated successfully in testing environment."

            from app.models.settings import Setting
            smtp_cfg = NotificationService.get_smtp_config()
            target = test_recipient or smtp_cfg["notification_email"] or smtp_cfg["user"]
            brand_name = Setting.get_value("company_name", "Scented Bubbles")

            if not target:
                return False, "Please specify a recipient email address to test."

            test_subject = f"[{brand_name}] Email Test — Verified Successfully! 🚀"
            test_body = (
                f"Congratulations!\n\n"
                f"Your email configuration for {brand_name} is active and working properly.\n"
                f"Customer order receipts, fulfillment milestone updates, and owner alerts will now be delivered reliably.\n\n"
                f"Delivered to: {target}"
            )
            test_html = f"""<div style="font-family: sans-serif; padding: 20px; background: #FAF8F5; border-radius: 8px;">
                <h2 style="color: #166534; margin-top: 0;">✅ Email Delivery Test Succeeded!</h2>
                <p style="color: #333; font-size: 14px; line-height: 1.6;">Your email configuration for <strong>{brand_name}</strong> is active and delivering properly.</p>
                <div style="background: #FFFFFF; padding: 12px; border-radius: 6px; border: 1px solid #E5E7EB; font-size: 13px;">
                    <strong>Recipient:</strong> {target}
                </div>
            </div>"""

            # 1. Test Brevo if configured
            brevo_key = (Setting.get_value("brevo_api_key") or current_app.config.get("BREVO_API_KEY") or "").strip()
            if brevo_key:
                ok = NotificationService._send_brevo_message(brevo_key, target, test_subject, test_body, html_body=test_html)
                if ok:
                    return True, f"Brevo HTTP API verified successfully! Test email delivered to {target} via HTTPS (Port 443)."
                return False, "Brevo HTTP API test failed. Please verify your Brevo API key."

            # 2. Test Resend if configured
            resend_key = (Setting.get_value("resend_api_key") or current_app.config.get("RESEND_API_KEY") or "").strip()
            if resend_key:
                ok = NotificationService._send_resend_message(resend_key, target, test_subject, test_body, html_body=test_html)
                if ok:
                    return True, f"Resend HTTP API verified successfully! Test email delivered to {target} via HTTPS (Port 443)."
                return False, "Resend HTTP API test failed. Please verify your Resend API key."

            # 3. Test Webhook if configured
            webhook_url = (Setting.get_value("email_webhook_url") or current_app.config.get("EMAIL_WEBHOOK_URL") or "").strip()
            if webhook_url:
                try:
                    import requests
                    resp = requests.post(
                        webhook_url,
                        json={"to": target, "subject": test_subject, "body": test_body, "html": test_html},
                        timeout=10,
                    )
                    if resp.status_code in (200, 201, 202):
                        return True, f"Email Webhook verified successfully! Test payload dispatched via HTTPS (Port 443)."
                    return False, f"Email Webhook returned status {resp.status_code}: {resp.text}"
                except Exception as we:
                    return False, f"Email Webhook request failed: {we}"

            # 4. Test SMTP
            smtp_host = smtp_cfg["host"]
            smtp_user = smtp_cfg["user"]
            smtp_pass = smtp_cfg["password"]
            port = smtp_cfg["port"]
            use_tls = smtp_cfg["use_tls"]

            if not (smtp_host and smtp_user and smtp_pass):
                return False, "SMTP Host, Username, and Password must be filled (or enter a Brevo API Key)."

            server = smtplib.SMTP(smtp_host, port, timeout=10)
            if use_tls:
                server.starttls()
            server.login(smtp_user, smtp_pass)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = test_subject
            msg["From"] = f"{brand_name} <{smtp_user}>"
            msg["To"] = target
            msg.attach(MIMEText(test_body, "plain", "utf-8"))
            msg.attach(MIMEText(test_html, "html", "utf-8"))
            server.send_message(msg)
            server.quit()

            return True, f"SMTP verified successfully! Test email delivered to {target} via {smtp_host}:{port}."
        except Exception as e:
            logger.exception("Email test probe failed")
            return False, f"Email test failed: {str(e)}"

    @staticmethod
    def _send_smtp_message(to_email: str, subject: str, body_text: str, html_body: str = None):
        """Universal email sender: automatically prefers HTTPS API (Brevo / Resend) over Port 443,
        falling back to SMTP (Port 587) for local testing and paid hosting.
        """
        try:
            # In testing/pytest mode, strictly suppress real SMTP connections and external email delivery
            if current_app and current_app.config.get("TESTING"):
                logger.info(f"[TESTING MODE] Suppressed email to {to_email}. Subject: '{subject}'")
                return True

            if not to_email or "@" not in to_email:
                return False

            from app.models.settings import Setting

            # 1. Check for Brevo API Key (Recommended for Render Free Tier - Port 443 HTTPS)
            brevo_key = (Setting.get_value("brevo_api_key") or current_app.config.get("BREVO_API_KEY") or "").strip()
            if brevo_key:
                if NotificationService._send_brevo_message(brevo_key, to_email, subject, body_text, html_body=html_body):
                    return True
                logger.warning("Brevo API send failed; falling back to alternative dispatch methods.")

            # 2. Check for Resend API Key (Port 443 HTTPS)
            resend_key = (Setting.get_value("resend_api_key") or current_app.config.get("RESEND_API_KEY") or "").strip()
            if resend_key:
                if NotificationService._send_resend_message(resend_key, to_email, subject, body_text, html_body=html_body):
                    return True
                logger.warning("Resend API send failed; falling back to alternative dispatch methods.")

            # 3. Check for Email Webhook URL (Google Apps Script / Webhook - Port 443 HTTPS)
            webhook_url = (Setting.get_value("email_webhook_url") or current_app.config.get("EMAIL_WEBHOOK_URL") or "").strip()
            if webhook_url:
                try:
                    import requests
                    resp = requests.post(
                        webhook_url,
                        json={
                            "to": to_email,
                            "subject": subject,
                            "body": body_text,
                            "html": html_body or f"<pre>{body_text}</pre>",
                        },
                        timeout=10,
                    )
                    if resp.status_code in (200, 201, 202):
                        logger.info(f"Email successfully delivered via Webhook to {to_email}")
                        return True
                    else:
                        logger.warning(f"Email webhook returned status {resp.status_code}: {resp.text}")
                except Exception as we:
                    logger.warning(f"Email webhook delivery failed: {we}")

            # 4. Standard SMTP Fallback (Port 587)
            smtp_cfg = NotificationService.get_smtp_config()
            smtp_host = smtp_cfg["host"]
            smtp_user = smtp_cfg["user"]
            smtp_pass = smtp_cfg["password"]
            port = smtp_cfg["port"]
            use_tls = smtp_cfg["use_tls"]

            if not (smtp_host and smtp_user and smtp_pass and to_email):
                logger.debug(f"SMTP not configured or recipient empty; skipping email to {to_email}.")
                return False

            brand_name = Setting.get_value("company_name", "Scented Bubbles")

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{brand_name} <{smtp_user}>"
            msg["To"] = to_email
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            if html_body:
                msg.attach(MIMEText(html_body, "html", "utf-8"))

            server = smtplib.SMTP(smtp_host, port, timeout=12)
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
                return False

            latest_pay = order.latest_payment
            utr_line = f"Bank UTR (Last 6 Digits): {latest_pay.utr}\n" if (latest_pay and latest_pay.utr) else ""
            utr_html = f"<div style='margin-bottom: 4px;'><strong>Bank UTR (Last 6 Digits):</strong> <span style='font-family: monospace; font-size: 14px; font-weight: 700; color: #1E40AF;'>{latest_pay.utr}</span></div>" if (latest_pay and latest_pay.utr) else ""

            items_lines = []
            items_html_rows = []
            for item in order.items:
                v_label = f" ({item.variant_label_snapshot})" if item.variant_label_snapshot else ""
                items_lines.append(f"  • {item.product_name_snapshot}{v_label} x {item.quantity} - ₹{item.total_price:,.2f}")
                items_html_rows.append(f"""
                <tr>
                    <td style='padding: 8px 12px; border-bottom: 1px solid #ECE7DF; font-size: 13px; color: #1A1A1A;'>
                        <strong>{item.product_name_snapshot}</strong>{v_label}
                    </td>
                    <td style='padding: 8px 12px; border-bottom: 1px solid #ECE7DF; font-size: 13px; text-align: center; color: #555555;'>
                        &times; {item.quantity}
                    </td>
                    <td style='padding: 8px 12px; border-bottom: 1px solid #ECE7DF; font-size: 13px; text-align: right; font-weight: 600; color: #1A1A1A;'>
                        ₹{item.total_price:,.2f}
                    </td>
                </tr>
                """)

            items_text = "\n".join(items_lines) if items_lines else "  No line items snapshot."
            items_html_table = "".join(items_html_rows)
            customer_email = NotificationService.get_customer_email(order) or "Not registered (Phone only)"
            admin_url = f"https://scentedbubble.in/admin/orders/{order.order_id}"

            subject = f"[{brand_name}] New Confirmed Order #{order.order_id} Received (₹{order.total_amount:,.2f})"
            body = (
                f"New Confirmed Order Received at {brand_name}!\n\n"
                f"Order ID: #{order.order_id}\n"
                f"Customer: {order.shipping_name}\n"
                f"Phone: {order.shipping_phone}\n"
                f"Email: {customer_email}\n"
                f"Total Amount: ₹{order.total_amount:,.2f}\n"
                f"Payment Method: {order.payment_method}\n"
                f"{utr_line}"
                f"Shipping Address:\n"
                f"{order.shipping_address_line1}, {order.shipping_city}, {order.shipping_state} - {order.shipping_pincode}\n\n"
                f"Ordered Items:\n{items_text}\n\n"
                f"Review order in admin portal: {admin_url}"
            )

            html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>New Confirmed Order #{order.order_id}</title></head>
<body style="margin: 0; padding: 20px 0; background-color: #FAF8F5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1A1A1A;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #FAF8F5; padding: 20px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%; background: #FFFFFF; border-radius: 12px; border: 1px solid #EAE5DC; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
          <tr>
            <td style="background: #1A1A1A; padding: 24px 32px; text-align: center;">
              <h1 style="margin: 0; color: #C5A880; font-family: Georgia, serif; font-size: 24px; letter-spacing: 0.05em; font-weight: normal;">{brand_name}</h1>
              <p style="margin: 4px 0 0; color: #A6998A; font-size: 11px; text-transform: uppercase; letter-spacing: 0.15em;">Store Admin Alert</p>
            </td>
          </tr>
          <tr>
            <td style="padding: 32px 32px 24px;">
              <div style="display: inline-block; background: #ECFDF5; color: #065F46; font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 99px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;">
                🎉 New Confirmed Order Received
              </div>
              <h2 style="margin: 0 0 10px; color: #1A1A1A; font-size: 22px; font-weight: 700;">Order #{order.order_id}</h2>
              <p style="margin: 0 0 16px; color: #555555; font-size: 15px; line-height: 1.5;">
                A new order has been placed by <strong>{order.shipping_name}</strong> for a total of <strong>₹{order.total_amount:,.2f}</strong>.
              </p>

              <div style="background: #FAF8F5; padding: 16px 20px; border-radius: 8px; border: 1px solid #ECE7DF; margin: 16px 0; font-size: 13px; line-height: 1.6;">
                <div style="margin-bottom: 4px;"><strong>Customer:</strong> {order.shipping_name} (<a href="tel:{order.shipping_phone}" style="color: #713F12; text-decoration: none; font-weight: 600;">{order.shipping_phone}</a>)</div>
                <div style="margin-bottom: 4px;"><strong>Email:</strong> {customer_email}</div>
                <div style="margin-bottom: 4px;"><strong>Payment Method:</strong> {order.payment_method}</div>
                {utr_html}
                <div style="margin-bottom: 4px;"><strong>Destination:</strong> {order.shipping_address_line1}, {order.shipping_city}, {order.shipping_state} - {order.shipping_pincode}</div>
              </div>

              <div style="margin: 20px 0;">
                <div style="font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: #713F12; margin-bottom: 8px;">Order Line Items</div>
                <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse; background: #FAF8F5; border-radius: 8px; overflow: hidden; border: 1px solid #ECE7DF;">
                  <thead>
                    <tr style="background: #F3EFEA; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #8C827A;">
                      <th style="padding: 8px 12px; text-align: left;">Product</th>
                      <th style="padding: 8px 12px; text-align: center;">Qty</th>
                      <th style="padding: 8px 12px; text-align: right;">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items_html_table}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colspan="2" style="padding: 10px 12px; font-weight: 700; font-size: 14px; text-align: right; color: #1A1A1A;">Total Amount:</td>
                      <td style="padding: 10px 12px; font-weight: 700; font-size: 15px; text-align: right; color: #713F12;">₹{order.total_amount:,.2f}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>

              <div style="text-align: center; margin-top: 24px;">
                <a href="{admin_url}" style="background: #1A1A1A; color: #FFFFFF; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-weight: 600; font-size: 14px; display: inline-block;">
                  Open Order in Admin Panel &rarr;
                </a>
              </div>
            </td>
          </tr>
          <tr>
            <td style="background: #FAF8F5; padding: 16px 32px; border-top: 1px solid #EAE5DC; text-align: center; font-size: 11px; color: #A6998A;">
              © {brand_name} Store Admin Notification System
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

            if NotificationService._send_smtp_message(to_email, subject, body, html_body=html_body):
                logger.info(f"Store owner notification email sent for order {order.order_id} to {to_email}")
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to send owner notification email for {order.order_id}: {e}")
            return False

    @staticmethod
    def send_customer_order_confirmation(order, brand_name: str = "Scented Bubbles", customer_email: str = None):
        """Sends rich itemized order confirmation receipt to customer if customer email is registered."""
        try:
            if not customer_email:
                customer_email = NotificationService.get_customer_email(order)

            # Strictly enforce: if no registered email, do not send!
            if not customer_email:
                logger.info(f"Order #{order.order_id}: No registered customer email found; skipping customer confirmation email.")
                return False

            from app.models.settings import Setting
            from datetime import timezone, timedelta

            # Formatting Date in IST
            ist_tz = timezone(timedelta(hours=5, minutes=30))
            order_dt = getattr(order, "confirmed_at", None) or getattr(order, "created_at", None)
            if order_dt:
                if order_dt.tzinfo is None:
                    order_dt = order_dt.replace(tzinfo=timezone.utc)
                date_str = order_dt.astimezone(ist_tz).strftime("%d %b %Y, %I:%M %p IST")
            else:
                date_str = "Recently Placed"

            # Payment details
            latest_pay = order.latest_payment
            utr_val = latest_pay.utr if (latest_pay and latest_pay.utr) else ""
            utr_text_line = f"Payment Reference / UTR: {utr_val}\n" if utr_val else ""
            utr_html_line = f"<div style='margin-top: 4px; color: #555555; font-size: 13px;'><strong>Payment Ref / UTR:</strong> {utr_val}</div>" if utr_val else ""

            pay_method_label = "UPI (Instant Scan & Pay)" if order.payment_method == "MANUAL_UPI" else (order.payment_method or "Online")
            pay_status_label = "Payment Verified & Confirmed" if order.payment_status == "PAID" else "Payment Reference Submitted (Under Verification)"

            # Delivery Fee
            delivery_charge_val = float(order.delivery_charge or 0)
            delivery_fee_str = "FREE (Pan-India Express)" if delivery_charge_val == 0 else f"₹{delivery_charge_val:,.2f}"

            # Items formatting
            items_lines = []
            items_html_rows = []
            for item in order.items:
                variant_info = f" ({item.variant_label_snapshot})" if item.variant_label_snapshot else ""
                items_lines.append(f"  • {item.product_name_snapshot}{variant_info} x {item.quantity} — ₹{float(item.total_price):,.2f}")
                items_html_rows.append(f"""
                <tr style="border-bottom: 1px solid #F0ECE4;">
                  <td style="padding: 12px 0;">
                    <div style="font-weight: 600; color: #1A1A1A; font-size: 14px;">{item.product_name_snapshot}</div>
                    <div style="color: #8C827A; font-size: 12px; margin-top: 2px;">{item.variant_label_snapshot or ''}</div>
                  </td>
                  <td style="padding: 12px 8px; text-align: center; color: #555555; font-size: 14px;">{item.quantity}</td>
                  <td style="padding: 12px 0; text-align: right; font-weight: 600; color: #1A1A1A; font-size: 14px;">₹{float(item.total_price):,.2f}</td>
                </tr>
                """)

            items_text = "\n".join(items_lines) if items_lines else "  Items confirmed."
            items_html = "".join(items_html_rows) if items_html_rows else "<tr><td colspan='3' style='padding: 10px; color: #888;'>Items confirmed.</td></tr>"

            # Address formatting
            addr_parts = [
                order.shipping_name,
                f"Phone: {order.shipping_phone}",
                order.shipping_address_line1,
            ]
            if order.shipping_address_line2:
                addr_parts.append(order.shipping_address_line2)
            addr_parts.append(f"{order.shipping_city}, {order.shipping_state} - {order.shipping_pincode}")

            address_text = "\n".join(addr_parts)
            address_html = "<br>".join(addr_parts)

            # Store info
            support_whatsapp = Setting.get_value("support_whatsapp", "919876543210")
            support_email = Setting.get_value("support_email", "care@scentedbubbles.com")
            track_url = "https://scentedbubble.in/track-order"

            subject = f"Your Order Confirmation #{order.order_id} - {brand_name}"

            # Plain text body
            body_text = (
                f"Hello {order.shipping_name},\n\n"
                f"Thank you for shopping with {brand_name}! We have received and confirmed your order.\n\n"
                f"==================================================\n"
                f"ORDER CONFIRMATION: #{order.order_id}\n"
                f"==================================================\n"
                f"Order Date: {date_str}\n"
                f"Payment Method: {pay_method_label}\n"
                f"Payment Status: {pay_status_label}\n"
                f"{utr_text_line}\n"
                f"ITEMS IN YOUR ORDER:\n"
                f"{items_text}\n\n"
                f"--------------------------------------------------\n"
                f"PRICE BREAKDOWN:\n"
                f"Subtotal: ₹{float(order.subtotal):,.2f}\n"
                f"Delivery Fee: {delivery_fee_str}\n"
                f"Total Amount: ₹{float(order.total_amount):,.2f}\n"
                f"--------------------------------------------------\n\n"
                f"SHIPPING ADDRESS:\n"
                f"{address_text}\n\n"
                f"Track your order anytime online at:\n"
                f"{track_url}\n\n"
                f"Need help with your order? Reach out on WhatsApp (+{support_whatsapp}) or email ({support_email}).\n\n"
                f"Warm regards,\n"
                f"The {brand_name} Team"
            )

            # HTML body
            html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Order Confirmation #{order.order_id}</title>
</head>
<body style="margin: 0; padding: 20px 0; background-color: #FAF8F5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1A1A1A;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #FAF8F5; padding: 20px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%; background: #FFFFFF; border-radius: 12px; border: 1px solid #EAE5DC; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
          
          <!-- Header -->
          <tr>
            <td style="background: #1A1A1A; padding: 28px 32px; text-align: center;">
              <h1 style="margin: 0; color: #C5A880; font-family: Georgia, serif; font-size: 26px; letter-spacing: 0.05em; font-weight: normal;">{brand_name}</h1>
              <p style="margin: 4px 0 0; color: #A6998A; font-size: 11px; text-transform: uppercase; letter-spacing: 0.15em;">Artisanal Fragrance & Luxury Diffusers</p>
            </td>
          </tr>

          <!-- Banner / Greeting -->
          <tr>
            <td style="padding: 32px 32px 20px; border-bottom: 1px solid #F0ECE4;">
              <div style="display: inline-block; background: #ECFDF5; color: #065F46; font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 99px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;">
                ✓ Order Confirmed
              </div>
              <h2 style="margin: 0 0 8px; color: #1A1A1A; font-size: 22px; font-weight: 700;">Thank You for Your Order, {order.shipping_name}!</h2>
              <p style="margin: 0; color: #666666; font-size: 14px; line-height: 1.5;">
                We have received and confirmed your order. Our team is carefully preparing your artisanal perfumes for courier dispatch.
              </p>
              
              <div style="margin-top: 18px; padding: 12px 16px; background: #FAF8F5; border-radius: 8px; border: 1px solid #ECE7DF; font-size: 13px;">
                <div style="margin-bottom: 4px;"><strong>Order ID:</strong> <span style="color: #713F12; font-weight: 700;">#{order.order_id}</span></div>
                <div style="color: #777777;">Placed on {date_str}</div>
              </div>
            </td>
          </tr>

          <!-- Items Table -->
          <tr>
            <td style="padding: 24px 32px 16px;">
              <h3 style="margin: 0 0 12px; color: #1A1A1A; font-size: 15px; text-transform: uppercase; letter-spacing: 0.08em;">Items in Your Order</h3>
              <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse;">
                <thead>
                  <tr style="border-bottom: 2px solid #EAE5DC; text-align: left; font-size: 11px; color: #8C827A; text-transform: uppercase; letter-spacing: 0.05em;">
                    <th style="padding-bottom: 8px;">Product</th>
                    <th style="padding-bottom: 8px; text-align: center;">Qty</th>
                    <th style="padding-bottom: 8px; text-align: right;">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {items_html}
                </tbody>
              </table>

              <!-- Financial Summary -->
              <table width="100%" cellspacing="0" cellpadding="0" style="margin-top: 16px; border-top: 1px solid #EAE5DC; font-size: 14px;">
                <tr>
                  <td style="padding: 8px 0; color: #666666;">Subtotal</td>
                  <td style="padding: 8px 0; text-align: right; color: #1A1A1A; font-weight: 500;">₹{float(order.subtotal):,.2f}</td>
                </tr>
                <tr>
                  <td style="padding: 8px 0; color: #666666;">Delivery Fee</td>
                  <td style="padding: 8px 0; text-align: right; color: #047857; font-weight: 600;">{delivery_fee_str}</td>
                </tr>
                <tr style="border-top: 2px solid #1A1A1A; font-size: 16px;">
                  <td style="padding: 12px 0; font-weight: 700; color: #1A1A1A;">Total Paid</td>
                  <td style="padding: 12px 0; text-align: right; font-weight: 700; color: #713F12; font-size: 18px;">₹{float(order.total_amount):,.2f}</td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Delivery & Payment Information Grid -->
          <tr>
            <td style="padding: 16px 32px 28px;">
              <table width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td width="48%" valign="top" style="background: #FAF8F5; padding: 16px; border-radius: 8px; border: 1px solid #ECE7DF;">
                    <div style="font-weight: 700; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #713F12; margin-bottom: 8px;">📍 Delivery Address</div>
                    <div style="font-size: 13px; color: #333333; line-height: 1.5;">
                      {address_html}
                    </div>
                  </td>
                  <td width="4%"></td>
                  <td width="48%" valign="top" style="background: #FAF8F5; padding: 16px; border-radius: 8px; border: 1px solid #ECE7DF;">
                    <div style="font-weight: 700; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #713F12; margin-bottom: 8px;">💳 Payment Details</div>
                    <div style="font-size: 13px; color: #333333; line-height: 1.5;">
                      <div><strong>Method:</strong> {pay_method_label}</div>
                      <div style="margin-top: 4px;"><strong>Status:</strong> {pay_status_label}</div>
                      {utr_html_line}
                    </div>
                  </td>
                </tr>
              </table>

              <!-- CTA Button -->
              <div style="text-align: center; margin-top: 28px;">
                <a href="{track_url}" style="background: #1A1A1A; color: #FFFFFF; text-decoration: none; padding: 13px 28px; border-radius: 6px; font-weight: 600; font-size: 14px; display: inline-block; letter-spacing: 0.02em;">
                  Track Your Order Online →
                </a>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background: #FAF8F5; padding: 24px 32px; border-top: 1px solid #EAE5DC; text-align: center; font-size: 12px; color: #8C827A; line-height: 1.5;">
              <p style="margin: 0 0 6px;">Questions regarding your order? We are here to help!</p>
              <p style="margin: 0 0 10px;">
                WhatsApp: <a href="https://wa.me/{support_whatsapp}" style="color: #713F12; font-weight: 600; text-decoration: none;">+{support_whatsapp}</a> &nbsp;|&nbsp; 
                Email: <a href="mailto:{support_email}" style="color: #713F12; font-weight: 600; text-decoration: none;">{support_email}</a>
              </p>
              <p style="margin: 0; font-size: 11px; color: #A6998A;">
                © {brand_name} • Handcrafted French Heritage Perfumes
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

            if NotificationService._send_smtp_message(customer_email, subject, body_text, html_body=html_body):
                logger.info(f"Customer confirmation email with order details sent to {customer_email} for order #{order.order_id}")
                return True
            return False

        except Exception as e:
            logger.warning(f"Failed to send customer order confirmation email: {e}")
            return False

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

    @staticmethod
    def notify_order_status_updated(order, new_status: str, brand_name: str = "Scented Bubbles", async_mode: bool = True):
        """Dispatches milestone emails to customer for CONFIRMED, PACKED, SHIPPED, DELIVERED, and CANCELLED (if enabled)."""
        try:
            from app.models.settings import Setting
            # Customer emails are skipped per user preference unless explicitly enabled
            if str(Setting.get_value("customer_emails_enabled", "false")).strip().lower() not in ("true", "1", "yes"):
                logger.info(f"Customer milestone emails disabled; skipping {new_status} status email for order {order.order_id}.")
                return

            order_notifs_enabled = Setting.get_value("order_notifications_enabled", "true")
            if str(order_notifs_enabled).strip().lower() in ("false", "0", "no", "disabled"):
                logger.info(f"Order notification emails are muted in Store Settings. Skipping milestone email for order {order.order_id}.")
                return

            customer_email = NotificationService.get_customer_email(order)
            if not customer_email:
                logger.info(f"Order #{order.order_id}: Customer does not have a registered email; skipping {new_status} status email.")
                return

            is_testing = current_app and current_app.config.get("TESTING")
            if is_testing or not async_mode:
                NotificationService._send_order_status_email(order, new_status, customer_email, brand_name)
                return

            import threading
            app = current_app._get_current_object()
            order_id = order.id
            thread = threading.Thread(
                target=NotificationService._async_status_worker,
                args=(app, order_id, new_status, customer_email, brand_name),
                daemon=True,
                name=f"StatusNotif-{order.order_id}-{new_status}",
            )
            thread.start()
            logger.info(f"Spawned background status notification worker for order #{order.order_id} -> {new_status}")

        except Exception as e:
            logger.exception(f"Failed to dispatch order status notification for {order.order_id}: {e}")

    @staticmethod
    def _async_status_worker(app, order_id: int, new_status: str, customer_email: str, brand_name: str):
        """Background worker thread executing milestone status email delivery."""
        with app.app_context():
            try:
                from app.models.orders import Order
                from app.extensions import db
                order = db.session.get(Order, order_id)
                if not order:
                    return
                NotificationService._send_order_status_email(order, new_status, customer_email, brand_name)
            except Exception as e:
                logger.exception(f"Background status notification failed for order ID {order_id}: {e}")

    @staticmethod
    def _send_order_status_email(order, new_status: str, customer_email: str, brand_name: str):
        """Formats and sends the milestone update email (CONFIRMED, PACKED, SHIPPED, DELIVERED, CANCELLED)."""
        try:
            from app.models.settings import Setting

            status_configs = {
                "CONFIRMED": {
                    "badge": "✓ Order Confirmed",
                    "badge_bg": "#ECFDF5",
                    "badge_color": "#065F46",
                    "title": "Your Order is Confirmed!",
                    "message": "We have verified your payment and confirmed your order. Our team is now carefully blending and preparing your artisanal fragrances for fulfillment.",
                    "subject": f"Your Order #{order.order_id} is Confirmed! — {brand_name}",
                },
                "PACKED": {
                    "badge": "📦 Order Packed",
                    "badge_bg": "#FEF3C7",
                    "badge_color": "#92400E",
                    "title": "Your Order is Packed & Ready!",
                    "message": "Every bottle in your order has been hand-inspected, wrapped in our protective luxury packaging, and securely sealed for courier handover.",
                    "subject": f"Your Order #{order.order_id} is Packed & Ready — {brand_name}",
                },
                "SHIPPED": {
                    "badge": "🚚 Dispatched & In Transit",
                    "badge_bg": "#EFF6FF",
                    "badge_color": "#1E40AF",
                    "title": "Your Order is On the Way!",
                    "message": "Great news! Your package has been handed over to our courier partner and is traveling to your doorstep.",
                    "subject": f"Your Order #{order.order_id} has been Shipped — {brand_name}",
                },
                "DELIVERED": {
                    "badge": "✨ Delivered",
                    "badge_bg": "#F3E8FF",
                    "badge_color": "#6B21A8",
                    "title": "Your Fragrance Package has Arrived!",
                    "message": "Your order has been delivered to your doorstep. We hope you love your new signature fragrances! Thank you for choosing Scented Bubbles.",
                    "subject": f"Your Order #{order.order_id} has been Delivered — {brand_name}",
                },
                "CANCELLED": {
                    "badge": "✕ Order Cancelled",
                    "badge_bg": "#FEE2E2",
                    "badge_color": "#991B1B",
                    "title": "Order Cancellation Notice",
                    "message": f"Your order #{order.order_id} has been cancelled." + (f" Reason: {order.cancellation_reason}" if order.cancellation_reason else ""),
                    "subject": f"Order #{order.order_id} Cancellation Update — {brand_name}",
                },
            }

            cfg = status_configs.get(new_status.upper())
            if not cfg:
                return False

            # Courier block for SHIPPED status
            courier_html = ""
            courier_text = ""
            if new_status.upper() == "SHIPPED":
                c_name = order.courier_name or "Express Courier Partner"
                t_num = order.tracking_number or "In Transit"
                t_url = order.tracking_url or "https://scentedbubble.in/track-order"
                courier_text = f"\nCOURIER DETAILS:\nCourier Partner: {c_name}\nTracking Number / AWB: {t_num}\nTrack URL: {t_url}\n"
                courier_html = f"""
                <div style="margin: 20px 0; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 16px;">
                    <div style="font-weight: 700; color: #1E40AF; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">🚚 Shipping &amp; Courier Details</div>
                    <div style="font-size: 14px; color: #1E3A8A; line-height: 1.6;">
                        <div><strong>Courier:</strong> {c_name}</div>
                        <div><strong>Tracking / AWB:</strong> {t_num}</div>
                        <div style="margin-top: 8px;"><a href="{t_url}" style="color: #1D4ED8; font-weight: 600; text-decoration: underline;">Click Here to Track Shipment &rarr;</a></div>
                    </div>
                </div>
                """

            # Items summary
            items_lines = []
            items_list_html = []
            for item in order.items:
                variant_info = f" ({item.variant_label_snapshot})" if item.variant_label_snapshot else ""
                items_lines.append(f"  • {item.product_name_snapshot}{variant_info} x {item.quantity}")
                items_list_html.append(f"<li style='margin-bottom: 4px;'><strong>{item.product_name_snapshot}</strong>{variant_info} &times; {item.quantity}</li>")
            items_text = "\n".join(items_lines) if items_lines else "  Items confirmed."
            items_html_block = f"<ul style='margin: 6px 0 0 16px; padding: 0; color: #555555; font-size: 13px;'>{''.join(items_list_html)}</ul>" if items_list_html else ""

            support_whatsapp = Setting.get_value("support_whatsapp", "919876543210")
            support_email = Setting.get_value("support_email", "care@scentedbubbles.com")
            track_url = "https://scentedbubble.in/track-order"

            body_text = (
                f"Hello {order.shipping_name},\n\n"
                f"{cfg['message']}\n\n"
                f"Order ID: #{order.order_id}\n"
                f"Status: {new_status}\n"
                f"{courier_text}\n"
                f"Items:\n{items_text}\n\n"
                f"Track status anytime: {track_url}\n\n"
                f"If you have any questions, reach out to us at {support_email} or WhatsApp +{support_whatsapp}.\n\n"
                f"Warm regards,\n"
                f"The {brand_name} Team"
            )

            html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{cfg['title']}</title></head>
<body style="margin: 0; padding: 20px 0; background-color: #FAF8F5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1A1A1A;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #FAF8F5; padding: 20px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%; background: #FFFFFF; border-radius: 12px; border: 1px solid #EAE5DC; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
          
          <!-- Header -->
          <tr>
            <td style="background: #1A1A1A; padding: 24px 32px; text-align: center;">
              <h1 style="margin: 0; color: #C5A880; font-family: Georgia, serif; font-size: 24px; letter-spacing: 0.05em; font-weight: normal;">{brand_name}</h1>
              <p style="margin: 4px 0 0; color: #A6998A; font-size: 11px; text-transform: uppercase; letter-spacing: 0.15em;">Order Status Update</p>
            </td>
          </tr>

          <!-- Message Card -->
          <tr>
            <td style="padding: 32px 32px 24px;">
              <div style="display: inline-block; background: {cfg['badge_bg']}; color: {cfg['badge_color']}; font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 99px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;">
                {cfg['badge']}
              </div>
              <h2 style="margin: 0 0 10px; color: #1A1A1A; font-size: 22px; font-weight: 700;">{cfg['title']}</h2>
              <p style="margin: 0 0 16px; color: #555555; font-size: 15px; line-height: 1.6;">
                {cfg['message']}
              </p>

              {courier_html}

              <div style="background: #FAF8F5; padding: 14px 18px; border-radius: 8px; border: 1px solid #ECE7DF; margin: 20px 0; font-size: 13px;">
                <div style="margin-bottom: 4px;"><strong>Order ID:</strong> <span style="color: #713F12; font-weight: 700;">#{order.order_id}</span></div>
                <div style="margin-bottom: 6px;"><strong>Recipient:</strong> {order.shipping_name} ({order.shipping_city}, {order.shipping_state})</div>
                <div style="border-top: 1px dashed #E5DFD5; padding-top: 8px; margin-top: 6px;">
                  <strong style="color: #1A1A1A;">Ordered Fragrances:</strong>
                  {items_html_block}
                </div>
              </div>

              <!-- Button -->
              <div style="text-align: center; margin-top: 24px;">
                <a href="{track_url}" style="background: #1A1A1A; color: #FFFFFF; text-decoration: none; padding: 12px 26px; border-radius: 6px; font-weight: 600; font-size: 14px; display: inline-block;">
                  Track Order Online &rarr;
                </a>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background: #FAF8F5; padding: 20px 32px; border-top: 1px solid #EAE5DC; text-align: center; font-size: 12px; color: #8C827A; line-height: 1.5;">
              <p style="margin: 0 0 6px;">Questions? WhatsApp: <a href="https://wa.me/{support_whatsapp}" style="color: #713F12; font-weight: 600; text-decoration: none;">+{support_whatsapp}</a> | Email: <a href="mailto:{support_email}" style="color: #713F12; font-weight: 600; text-decoration: none;">{support_email}</a></p>
              <p style="margin: 0; font-size: 11px; color: #A6998A;">© {brand_name} • Handcrafted French Heritage Perfumes</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

            return NotificationService._send_smtp_message(customer_email, cfg["subject"], body_text, html_body=html_body)

        except Exception as e:
            logger.warning(f"Failed to send milestone update email for {order.order_id}: {e}")
            return False

