from flask import render_template
from flask_login import login_required, current_user
from decimal import Decimal
from app.extensions import db
from app.models.procurement import Product, PurchaseOrder
from app.models.warehouse import StockTransferRequest
from app.models.sales import Sale
from app.models.accounting import AccountsPayable
from . import main_bp


@main_bp.route('/')
@login_required
def dashboard():
    role = current_user.role.name

    low_warehouse_stock = []
    low_shelf_stock = []
    pending_transfers = []
    pending_pos = []
    unpaid_payables = []
    recent_sales = []

    products = Product.query.filter_by(is_active=True).all()

    if current_user.has_permission('view_inventory'):
        low_warehouse_stock = [
            p for p in products
            if (p.warehouse_stock or Decimal('0')) <=
               (p.warehouse_reorder_threshold or Decimal('0'))
            and p.warehouse_reorder_threshold > 0
        ]
        low_shelf_stock = [
            p for p in products
            if (p.shelf_stock or Decimal('0')) <=
               (p.shelf_reorder_threshold or Decimal('0'))
            and p.shelf_reorder_threshold > 0
        ]

    if current_user.has_permission('approve_transfers'):
        pending_transfers = StockTransferRequest.query.filter_by(
            status='Pending'
        ).order_by(StockTransferRequest.requested_at.desc()).all()

    if current_user.has_permission('approve_po'):
        pending_pos = PurchaseOrder.query.filter_by(
            status='Submitted'
        ).order_by(PurchaseOrder.submitted_at.desc()).all()

    if current_user.has_permission('manage_payables'):
        unpaid_payables = AccountsPayable.query.filter(
            AccountsPayable.status != 'Paid'
        ).order_by(AccountsPayable.due_date).limit(5).all()

    if current_user.has_permission('create_sale') or \
       current_user.has_permission('view_invoices'):
        recent_sales = Sale.query.filter_by(
            status='Completed'
        ).order_by(Sale.created_at.desc()).limit(5).all()

    return render_template('main/dashboard.html',
        low_warehouse_stock=low_warehouse_stock,
        low_shelf_stock=low_shelf_stock,
        pending_transfers=pending_transfers,
        pending_pos=pending_pos,
        unpaid_payables=unpaid_payables,
        recent_sales=recent_sales
    )