from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional
from app.extensions import db
from app.models.payments import Payment
from app.models.orders import Order


class PaymentError(Exception):
    """Base exception for payment operations."""
    pass


class DuplicateUTRError(PaymentError):
    """Raised when a submitted UPI UTR has already been recorded."""
    pass


class PaymentService(ABC):
    """Abstract interface for all store payment providers."""

    @abstractmethod
    def create_payment(self, order: Order, **kwargs) -> Payment:
        pass

    @abstractmethod
    def verify_payment(self, payment: Payment, **kwargs) -> bool:
        pass

    @abstractmethod
    def refund_payment(self, payment: Payment, **kwargs) -> bool:
        pass


class ManualUPIPaymentService(PaymentService):
    """Manual UPI 'Scan & Pay' flow.
    
    Orders start strictly as PENDING_VERIFICATION and are NEVER auto-verified.
    The customer provides the 12-digit UTR/Ref number, which carries a database UNIQUE constraint.
    Verification to PAID or rejection to FAILED is strictly manual by the store admin.
    """

    def create_payment(self, order: Order, utr: Optional[str] = None, notes: Optional[str] = None, **kwargs) -> Payment:
        clean_utr = utr.strip() if utr else None
        
        if clean_utr:
            # Check unique constraint before insertion to provide clean application exception
            existing = Payment.query.filter_by(utr=clean_utr).first()
            if existing and existing.order_id != order.id:
                raise DuplicateUTRError(f"The transaction reference (UTR) '{clean_utr}' has already been registered.")

        payment = Payment(
            order_id=order.id,
            payment_method=Payment.METHOD_MANUAL_UPI,
            amount=Decimal(str(order.total_amount)),
            utr=clean_utr,
            status=Payment.STATUS_PENDING_VERIFICATION,
            notes=notes or "Customer UPI submission awaiting admin verification",
        )
        db.session.add(payment)
        order.payment_status = Order.PAYMENT_PENDING_VERIFICATION
        return payment

    def verify_payment(self, payment: Payment, admin_notes: Optional[str] = None, **kwargs) -> bool:
        """Invoked exclusively by admin upon confirming bank receipt."""
        payment.status = Payment.STATUS_PAID
        payment.order.payment_status = Order.PAYMENT_PAID
        if admin_notes:
            payment.notes = f"{payment.notes or ''}\nAdmin Verified: {admin_notes}".strip()
        return True

    def refund_payment(self, payment: Payment, admin_notes: Optional[str] = None, **kwargs) -> bool:
        """Mark payment as refunded."""
        payment.status = Payment.STATUS_REFUNDED
        payment.order.payment_status = Order.PAYMENT_REFUNDED
        if admin_notes:
            payment.notes = f"{payment.notes or ''}\nAdmin Refunded: {admin_notes}".strip()
        return True


class CashOnDeliveryPaymentService(PaymentService):
    """Cash on Delivery (COD) payment flow."""

    def create_payment(self, order: Order, notes: Optional[str] = None, **kwargs) -> Payment:
        payment = Payment(
            order_id=order.id,
            payment_method=Payment.METHOD_COD,
            amount=Decimal(str(order.total_amount)),
            utr=None,
            status=Payment.STATUS_PENDING_VERIFICATION,
            notes=notes or "Cash on Delivery",
        )
        db.session.add(payment)
        order.payment_status = Order.PAYMENT_PENDING_VERIFICATION
        return payment

    def verify_payment(self, payment: Payment, admin_notes: Optional[str] = None, **kwargs) -> bool:
        """Marked paid by admin or courier integration upon package handover."""
        payment.status = Payment.STATUS_PAID
        payment.order.payment_status = Order.PAYMENT_PAID
        if admin_notes:
            payment.notes = f"{payment.notes or ''}\nCOD Received: {admin_notes}".strip()
        return True

    def refund_payment(self, payment: Payment, admin_notes: Optional[str] = None, **kwargs) -> bool:
        payment.status = Payment.STATUS_REFUNDED
        payment.order.payment_status = Order.PAYMENT_REFUNDED
        return True


class RazorpayPaymentService(PaymentService):
    """Documented stub for Razorpay gateway integration."""

    def create_payment(self, order: Order, **kwargs) -> Payment:
        raise NotImplementedError("Razorpay gateway is not configured in v1.")

    def verify_payment(self, payment: Payment, **kwargs) -> bool:
        raise NotImplementedError("Razorpay gateway is not configured in v1.")

    def refund_payment(self, payment: Payment, **kwargs) -> bool:
        raise NotImplementedError("Razorpay gateway is not configured in v1.")


def get_payment_service(method: str) -> PaymentService:
    """Factory returns payment service for given method."""
    method_upper = (method or "").upper()
    if method_upper in ("MANUAL_UPI", "UPI"):
        return ManualUPIPaymentService()
    elif method_upper == "COD":
        return CashOnDeliveryPaymentService()
    elif method_upper == "RAZORPAY":
        return RazorpayPaymentService()
    raise ValueError(f"Unsupported payment method: {method}")
