import urllib.parse
import re
import logging

logger = logging.getLogger(__name__)


def clean_phone_number(phone: str, default_country_code: str = "91") -> str:
    """Sanitizes phone number for WhatsApp wa.me links, ensuring international format."""
    digits = re.sub(r"\D", "", str(phone or ""))
    if len(digits) == 10:
        return f"{default_country_code}{digits}"
    return digits


def build_customer_whatsapp_link(order, store_phone: str, brand_name: str = "Scented Bubbles") -> str:
    """Builds a WhatsApp click-to-chat link for the customer to send their order details to the store."""
    try:
        phone = clean_phone_number(store_phone)
        items_summary = ", ".join(f"{it.product_name_snapshot} ({it.variant_label_snapshot}) x{it.quantity}" for it in order.items)
        
        message = (
            f"Hello {brand_name}! 👋\n\n"
            f"I have placed an order with your store:\n"
            f"• *Order ID:* {order.order_id}\n"
            f"• *Items:* {items_summary}\n"
            f"• *Total Amount:* ₹{order.total_amount}\n"
            f"• *Payment Method:* {order.payment_method}\n"
            f"• *Payment Status:* {order.payment_status}\n\n"
            f"Please confirm my order. Thank you!"
        )
        encoded = urllib.parse.quote(message)
        return f"https://wa.me/{phone}?text={encoded}"
    except Exception as e:
        logger.error(f"Error building customer WhatsApp link: {e}")
        return ""


def build_admin_whatsapp_link(order, brand_name: str = "Scented Bubbles") -> str:
    """Builds a WhatsApp link for the admin to contact the customer regarding order status."""
    try:
        phone = clean_phone_number(order.shipping_phone)
        message = (
            f"Hello {order.shipping_name}, greetings from *{brand_name}*! ✨\n\n"
            f"Regarding your order *#{order.order_id}* (Total: ₹{order.total_amount}):\n"
            f"Status: {order.order_status}\n\n"
            f"Please let us know if you need any assistance!"
        )
        encoded = urllib.parse.quote(message)
        return f"https://wa.me/{phone}?text={encoded}"
    except Exception as e:
        logger.error(f"Error building admin WhatsApp link: {e}")
        return ""
