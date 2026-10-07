import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy import func, desc, case
from app.extensions import db
from app.models.orders import Order
from app.models.order_items import OrderItem
from app.models.products import Product
from app.models.product_variants import ProductVariant
from app.models.categories import Category


def _get_date_col(date_basis: str = "placed"):
    """Returns Order.created_at for booking date cohort or Order.updated_at for activity/fulfillment cohort."""
    return Order.updated_at if date_basis == "activity" else Order.created_at


def _format_month(col):
    """Database-agnostic month string (%Y-%m / YYYY-MM)."""
    bind = db.session.get_bind()
    if bind and bind.dialect.name.startswith("postgres"):
        return func.to_char(col, "YYYY-MM")
    return func.strftime("%Y-%m", col)


def _format_hour(col):
    """Database-agnostic hour string (%H / HH24)."""
    bind = db.session.get_bind()
    if bind and bind.dialect.name.startswith("postgres"):
        return func.to_char(col, "HH24")
    return func.strftime("%H", col)


def get_summary_kpis(
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    date_basis: str = "placed",
) -> Dict[str, Any]:
    """Lightweight aggregate KPIs calculated strictly inside SQL engine."""
    date_col = _get_date_col(date_basis)
    query = db.session.query(
        func.count(Order.id).label("total_orders"),
        func.coalesce(func.sum(case((Order.order_status != Order.STATUS_CANCELLED, 1), else_=0)), 0).label("valid_orders"),
        func.coalesce(func.sum(case((Order.order_status != Order.STATUS_CANCELLED, Order.total_amount), else_=0)), 0).label("net_revenue"),
        func.coalesce(func.sum(case((Order.payment_status == Order.PAYMENT_PAID, Order.total_amount), else_=0)), 0).label("paid_revenue"),
        func.coalesce(func.sum(case((Order.payment_status == Order.PAYMENT_PENDING_VERIFICATION, 1), else_=0)), 0).label("pending_payments_count"),
        func.coalesce(func.sum(case((Order.order_status == Order.STATUS_PENDING, 1), else_=0)), 0).label("pending_orders_count"),
        func.coalesce(func.sum(case((Order.order_status == Order.STATUS_SHIPPED, 1), else_=0)), 0).label("shipped_orders_count"),
        func.coalesce(func.sum(case((Order.order_status == Order.STATUS_DELIVERED, 1), else_=0)), 0).label("delivered_orders_count"),
    )

    if start_date:
        query = query.filter(date_col >= datetime.datetime.combine(start_date, datetime.time.min))
    if end_date:
        query = query.filter(date_col <= datetime.datetime.combine(end_date, datetime.time.max))

    result = query.one()
    total_orders = result.total_orders or 0
    valid_orders = result.valid_orders or 0
    net_revenue = Decimal(str(result.net_revenue or 0.00))
    divisor = valid_orders if valid_orders > 0 else total_orders
    aov = (net_revenue / divisor) if divisor > 0 else Decimal("0.00")

    # Real-time active store fulfillment pipeline across all orders in database
    live_pipeline = db.session.query(
        func.coalesce(func.sum(case((Order.order_status == Order.STATUS_DELIVERED, 1), else_=0)), 0).label("delivered_total"),
        func.coalesce(func.sum(case((Order.order_status == Order.STATUS_SHIPPED, 1), else_=0)), 0).label("shipped_total"),
        func.coalesce(func.sum(case((Order.order_status == Order.STATUS_PENDING, 1), else_=0)), 0).label("pending_total"),
        func.coalesce(func.sum(case((Order.payment_status == Order.PAYMENT_PENDING_VERIFICATION, 1), else_=0)), 0).label("pending_upi_total"),
    ).one()

    return {
        "total_orders": total_orders,
        "valid_orders": valid_orders,
        "net_revenue": net_revenue,
        "paid_revenue": Decimal(str(result.paid_revenue or 0.00)),
        "aov": aov,
        "pending_payments_count": result.pending_payments_count or 0,
        "pending_orders_count": result.pending_orders_count or 0,
        "shipped_orders_count": result.shipped_orders_count or 0,
        "delivered_orders_count": result.delivered_orders_count or 0,
        "live_store_delivered": live_pipeline.delivered_total or 0,
        "live_store_shipped": live_pipeline.shipped_total or 0,
        "live_store_pending": live_pipeline.pending_total or 0,
        "live_store_pending_upi": live_pipeline.pending_upi_total or 0,
    }


def get_daily_revenue_trend(
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    date_basis: str = "placed",
) -> Dict[str, Any]:
    """1. Daily revenue time series for Chart.js. SQL GROUP BY date only."""
    dt_col = _get_date_col(date_basis)
    date_expr = func.date(dt_col)

    query = db.session.query(
        date_expr.label("day"),
        func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
        func.count(Order.id).label("orders_count"),
    ).filter(Order.order_status != Order.STATUS_CANCELLED)

    if start_date:
        query = query.filter(dt_col >= datetime.datetime.combine(start_date, datetime.time.min))
    if end_date:
        query = query.filter(dt_col <= datetime.datetime.combine(end_date, datetime.time.max))

    rows = query.group_by("day").order_by("day").all()

    # If explicit date range provided within 90 days, fill missing days for smooth charts
    if start_date and end_date and (end_date - start_date).days <= 90:
        day_map = {str(r.day): (float(r.revenue), r.orders_count) for r in rows}
        cur = start_date
        all_labels = []
        all_rev = []
        all_orders = []
        while cur <= end_date:
            cur_str = cur.strftime("%Y-%m-%d")
            all_labels.append(cur_str)
            rev, ords = day_map.get(cur_str, (0.0, 0))
            all_rev.append(rev)
            all_orders.append(ords)
            cur += datetime.timedelta(days=1)
        return {
            "labels": all_labels,
            "revenue": all_rev,
            "orders": all_orders,
        }

    labels = [str(r.day) for r in rows]
    revenue_data = [float(r.revenue) for r in rows]
    order_counts = [r.orders_count for r in rows]

    return {
        "labels": labels,
        "revenue": revenue_data,
        "orders": order_counts,
    }


def get_monthly_revenue_trend() -> Dict[str, Any]:
    """2. Monthly revenue trend for Chart.js."""
    month_col = _format_month(Order.created_at)

    rows = db.session.query(
        month_col.label("month"),
        func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
        func.count(Order.id).label("orders_count"),
    ).filter(Order.order_status != Order.STATUS_CANCELLED)\
     .group_by("month")\
     .order_by("month")\
     .all()

    return {
        "labels": [str(r.month) for r in rows],
        "revenue": [float(r.revenue) for r in rows],
        "orders": [r.orders_count for r in rows],
    }


def get_orders_by_status(start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """3. Order status distribution."""
    query = db.session.query(
        Order.order_status,
        func.count(Order.id).label("count")
    )
    if start_date:
        query = query.filter(Order.created_at >= datetime.datetime.combine(start_date, datetime.time.min))
    if end_date:
        query = query.filter(Order.created_at <= datetime.datetime.combine(end_date, datetime.time.max))

    rows = query.group_by(Order.order_status).all()
    return {
        "labels": [r.order_status for r in rows],
        "data": [r.count for r in rows],
    }


def get_orders_by_payment_status(start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """4. Payment status distribution."""
    query = db.session.query(
        Order.payment_status,
        func.count(Order.id).label("count")
    )
    if start_date:
        query = query.filter(Order.created_at >= datetime.datetime.combine(start_date, datetime.time.min))
    if end_date:
        query = query.filter(Order.created_at <= datetime.datetime.combine(end_date, datetime.time.max))

    rows = query.group_by(Order.payment_status).all()
    return {
        "labels": [r.payment_status for r in rows],
        "data": [r.count for r in rows],
    }


def get_top_bestsellers(limit: int = 10, start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """5. Top best selling products by units sold."""
    query = db.session.query(
        OrderItem.product_name_snapshot.label("product_name"),
        func.sum(OrderItem.quantity).label("units_sold"),
        func.sum(OrderItem.total_price).label("total_revenue"),
    ).join(Order, OrderItem.order_id == Order.id)\
     .filter(Order.order_status != Order.STATUS_CANCELLED)

    if start_date:
        query = query.filter(Order.created_at >= datetime.datetime.combine(start_date, datetime.time.min))
    if end_date:
        query = query.filter(Order.created_at <= datetime.datetime.combine(end_date, datetime.time.max))

    rows = query.group_by(OrderItem.product_name_snapshot)\
                .order_by(desc("units_sold"), desc("total_revenue"))\
                .limit(limit)\
                .all()

    return {
        "labels": [r.product_name for r in rows],
        "units": [r.units_sold for r in rows],
        "revenue": [float(r.total_revenue) for r in rows],
        "top_products": [
            {
                "name": r.product_name,
                "units": r.units_sold,
                "revenue": float(r.total_revenue),
            }
            for r in rows
        ],
    }


def get_sales_by_category(start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """6. Sales revenue breakdown by Category."""
    query = db.session.query(
        func.coalesce(Category.name, "Other / Bundles").label("category_name"),
        func.sum(OrderItem.total_price).label("category_revenue"),
        func.sum(OrderItem.quantity).label("category_units"),
    ).select_from(OrderItem)\
     .join(Order, OrderItem.order_id == Order.id)\
     .outerjoin(ProductVariant, OrderItem.product_variant_id == ProductVariant.id)\
     .outerjoin(Product, ProductVariant.product_id == Product.id)\
     .outerjoin(Category, Product.category_id == Category.id)\
     .filter(Order.order_status != Order.STATUS_CANCELLED)

    if start_date:
        query = query.filter(Order.created_at >= datetime.datetime.combine(start_date, datetime.time.min))
    if end_date:
        query = query.filter(Order.created_at <= datetime.datetime.combine(end_date, datetime.time.max))

    rows = query.group_by(Category.name)\
                .order_by(desc("category_revenue"))\
                .all()

    total_cat_rev = sum(float(r.category_revenue or 0) for r in rows)
    return {
        "labels": [r.category_name for r in rows],
        "revenue": [float(r.category_revenue) for r in rows],
        "units": [r.category_units for r in rows],
        "breakdown": [
            {
                "name": r.category_name,
                "revenue": float(r.category_revenue),
                "units": r.category_units,
                "share": round((float(r.category_revenue) / total_cat_rev * 100), 1) if total_cat_rev > 0 else 0,
            }
            for r in rows
        ],
    }


def get_orders_by_hour(start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """7. Hourly peak purchasing distribution (00 to 23)."""
    hour_col = _format_hour(Order.created_at)
    query = db.session.query(
        hour_col.label("hour"),
        func.count(Order.id).label("count")
    ).filter(Order.order_status != Order.STATUS_CANCELLED)

    if start_date:
        query = query.filter(Order.created_at >= datetime.datetime.combine(start_date, datetime.time.min))
    if end_date:
        query = query.filter(Order.created_at <= datetime.datetime.combine(end_date, datetime.time.max))

    rows = query.group_by("hour")\
                .order_by("hour")\
                .all()

    return {
        "labels": [f"{r.hour}:00" for r in rows],
        "data": [r.count for r in rows],
    }
