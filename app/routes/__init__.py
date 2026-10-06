from app.routes.main import main_bp
from app.routes.products import products_bp
from app.routes.cart import cart_bp
from app.routes.checkout import checkout_bp
from app.routes.orders import orders_bp
from app.routes.admin import admin_bp
from app.routes.account import account_bp

__all__ = [
    "main_bp",
    "products_bp",
    "cart_bp",
    "checkout_bp",
    "orders_bp",
    "admin_bp",
    "account_bp",
]
