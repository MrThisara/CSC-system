from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from decimal import Decimal
from app.extensions import db
from app.models.procurement import Product, Supplier, PurchaseOrder, LandedCost
from app.models.sales import Sale, SaleItem
from app.models.accounting import AccountsPayable
from app.models.warehouse import StockMovement
from sqlalchemy import func
import datetime
from . import reporting_bp


def require_permission(permission_name):
    if not current_user.has_permission(permission_name):
        return False
    return True


@reporting_bp.route('/')
@login_required
def reports():
    if not require_permission('view_reports'):
        return redirect(url_for('main.dashboard'))

    # ── Report 1: Profit margin per product ───────────────
    products = Product.query.filter_by(is_active=True).all()
    profit_margins = []
    for p in products:
        if p.avco_cost and p.avco_cost > 0:
            margin = p.selling_price - p.avco_cost
            margin_pct = (margin / p.selling_price * 100) if p.selling_price > 0 else 0
        else:
            margin = p.selling_price
            margin_pct = Decimal('100')
        profit_margins.append({
            'product': p,
            'margin': margin,
            'margin_pct': round(margin_pct, 2)
        })
    profit_margins.sort(key=lambda x: x['margin_pct'], reverse=True)

    # ── Report 2: Fast vs slow moving stock ───────────────
    thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    sales_volume = db.session.query(
        SaleItem.product_id,
        func.sum(SaleItem.quantity).label('total_sold')
    ).join(Sale).filter(
        Sale.created_at >= thirty_days_ago,
        Sale.status == 'Completed'
    ).group_by(SaleItem.product_id).all()

    sales_map = {row.product_id: row.total_sold for row in sales_volume}
    stock_movement = []
    for p in products:
        sold = sales_map.get(p.id, Decimal('0'))
        stock_movement.append({
            'product': p,
            'sold_30_days': sold,
            'status': 'Fast' if sold > 0 else 'Slow'
        })
    stock_movement.sort(key=lambda x: x['sold_30_days'], reverse=True)

    # ── Report 3: What we owe suppliers ───────────────────
    unpaid_payables = AccountsPayable.query.filter(
        AccountsPayable.status != 'Paid'
    ).order_by(AccountsPayable.amount_due.desc()).all()
    total_owed = sum(
        (p.amount_due - p.amount_paid) for p in unpaid_payables
    )

    # ── Report 4: Total inventory value ───────────────────
    total_inventory_value = sum(
        (p.warehouse_stock or Decimal('0')) * (p.avco_cost or Decimal('0'))
        for p in products
    )

    # ── Report 5: Best value supplier ─────────────────────
    supplier_costs = []
    suppliers = Supplier.query.filter_by(is_active=True).all()
    for supplier in suppliers:
        pos = PurchaseOrder.query.filter_by(
            supplier_id=supplier.id,
            status='Goods Received'
        ).all()
        if not pos:
            continue
        total_product_cost = Decimal('0')
        total_landed = Decimal('0')
        total_units = Decimal('0')
        for po in pos:
            for item in po.items:
                unit_cost_jpy = (item.unit_price or Decimal('0')) * \
                                (po.exchange_rate or Decimal('1'))
                total_product_cost += unit_cost_jpy * (item.quantity_received
                                                        or Decimal('0'))
                total_units += item.quantity_received or Decimal('0')
            for shipment in po.shipments:
                for lc in shipment.landed_costs:
                    total_landed += (lc.total or Decimal('0')) * \
                                    (lc.exchange_rate or Decimal('1'))
        if total_units > 0:
            avg_total_cost = (total_product_cost + total_landed) / total_units
        else:
            avg_total_cost = Decimal('0')
        supplier_costs.append({
            'supplier': supplier,
            'total_product_cost': total_product_cost,
            'total_landed': total_landed,
            'total_units': total_units,
            'avg_total_cost_per_unit': round(avg_total_cost, 4)
        })
    supplier_costs.sort(key=lambda x: x['avg_total_cost_per_unit'])

    # ── Report 6: Currency fluctuation cost ───────────────
    first_of_month = datetime.datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0)
    monthly_pos = PurchaseOrder.query.filter(
        PurchaseOrder.created_at >= first_of_month,
        PurchaseOrder.status == 'Goods Received'
    ).all()
    fx_impact = []
    for po in monthly_pos:
        if not po.exchange_rate or not po.currency:
            continue
        for item in po.items:
            qty = item.quantity_received or Decimal('0')
            actual_cost_jpy = item.unit_price * po.exchange_rate * qty
            base_cost_jpy = item.unit_price * qty
            fx_loss = actual_cost_jpy - base_cost_jpy
            if fx_loss != 0:
                fx_impact.append({
                    'po': po,
                    'product': item.product,
                    'currency': po.currency.code,
                    'exchange_rate': po.exchange_rate,
                    'fx_loss': round(fx_loss, 2)
                })
    total_fx_loss = sum(f['fx_loss'] for f in fx_impact)

    return render_template('reporting/reports.html',
        profit_margins=profit_margins,
        stock_movement=stock_movement,
        unpaid_payables=unpaid_payables,
        total_owed=total_owed,
        total_inventory_value=total_inventory_value,
        supplier_costs=supplier_costs,
        fx_impact=fx_impact,
        total_fx_loss=total_fx_loss
    )