from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from decimal import Decimal
from app.extensions import db
from app.models.procurement import Product
from app.models.sales import (BulkBuyer, Sale, SaleItem, BulkOrder,
                               Invoice, CustomerReturn)
from app.models.warehouse import StockMovement, StockTransferRequest
from app.models.admin import CompanySettings
from app.models.audit import AuditLog
from . import sales_bp
from .forms import (BulkBuyerForm, SaleItemForm, WalkInSaleForm, BulkOrderForm,
                    TransferRequestForm, CustomerReturnForm, DeliveryStatusForm)
import datetime


def log(tier, action, entity_type, entity_id, description, old_value=None, new_value=None):
    entry = AuditLog(
        tier=tier,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        old_value=old_value,
        new_value=new_value,
        performed_by_id=current_user.id,
        ip_address=request.remote_addr
    )
    db.session.add(entry)


def require_permission(permission_name):
    if not current_user.has_permission(permission_name):
        flash('You do not have permission to access that page.', 'danger')
        return False
    return True


def generate_sale_number():
    year = datetime.datetime.now().year
    last = Sale.query.filter(
        Sale.sale_number.like(f'SALE-{year}-%')
    ).order_by(Sale.id.desc()).first()
    if last:
        last_num = int(last.sale_number.split('-')[-1])
        return f'SALE-{year}-{str(last_num + 1).zfill(4)}'
    return f'SALE-{year}-0001'


def generate_invoice_number():
    year = datetime.datetime.now().year
    last = Invoice.query.filter(
        Invoice.invoice_number.like(f'INV-{year}-%')
    ).order_by(Invoice.id.desc()).first()
    if last:
        last_num = int(last.invoice_number.split('-')[-1])
        return f'INV-{year}-{str(last_num + 1).zfill(4)}'
    return f'INV-{year}-0001'


def get_tax_rate():
    settings = CompanySettings.query.first()
    return settings.tax_rate if settings else Decimal('0.10')


# ── Bulk Buyers ────────────────────────────────────────────

@sales_bp.route('/bulk-buyers')
@login_required
def bulk_buyers():
    if not require_permission('manage_customers'):
        return redirect(url_for('main.dashboard'))
    all_buyers = BulkBuyer.query.order_by(BulkBuyer.full_name).all()
    form = BulkBuyerForm()
    return render_template('sales/bulk_buyers.html', buyers=all_buyers, form=form)


@sales_bp.route('/bulk-buyers/add', methods=['POST'])
@login_required
def add_bulk_buyer():
    if not require_permission('manage_customers'):
        return redirect(url_for('main.dashboard'))
    form = BulkBuyerForm()
    if form.validate_on_submit():
        buyer = BulkBuyer(
            full_name=form.full_name.data,
            phone=form.phone.data,
            email=form.email.data,
            delivery_address=form.delivery_address.data,
            created_by_id=current_user.id
        )
        db.session.add(buyer)
        db.session.flush()
        log('standard', 'bulk_buyer_created', 'bulk_buyer', buyer.id,
            f'Bulk buyer {buyer.full_name} created.')
        db.session.commit()
        flash(f'Bulk buyer {buyer.full_name} added.', 'success')
    return redirect(url_for('sales.bulk_buyers'))


@sales_bp.route('/bulk-buyers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bulk_buyer(id):
    if not require_permission('manage_customers'):
        return redirect(url_for('main.dashboard'))
    buyer = BulkBuyer.query.get_or_404(id)
    form = BulkBuyerForm(obj=buyer)
    if form.validate_on_submit():
        buyer.full_name = form.full_name.data
        buyer.phone = form.phone.data
        buyer.email = form.email.data
        buyer.delivery_address = form.delivery_address.data
        log('standard', 'bulk_buyer_edited', 'bulk_buyer', buyer.id,
            f'Bulk buyer {buyer.full_name} edited.')
        db.session.commit()
        flash(f'{buyer.full_name} updated.', 'success')
        return redirect(url_for('sales.bulk_buyers'))
    return render_template('sales/edit_bulk_buyer.html', form=form, buyer=buyer)


# ── Walk-in Sale ───────────────────────────────────────────

@sales_bp.route('/new-sale', methods=['GET', 'POST'])
@login_required
def new_sale():
    if not require_permission('create_sale'):
        return redirect(url_for('main.dashboard'))
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    return render_template('sales/new_sale.html', products=products)


@sales_bp.route('/new-sale/process', methods=['POST'])
@login_required
def process_sale():
    if not require_permission('create_sale'):
        return redirect(url_for('main.dashboard'))

    tax_rate = get_tax_rate()
    sale_number = generate_sale_number()

    sale = Sale(
        sale_number=sale_number,
        sale_type='walk_in',
        status='Completed',
        tax_rate=tax_rate,
        created_by_id=current_user.id
    )
    db.session.add(sale)
    db.session.flush()

    subtotal = Decimal('0')
    product_ids = request.form.getlist('product_id')
    quantities = request.form.getlist('quantity')

    valid_items = [(pid, qty) for pid, qty in zip(product_ids, quantities)
               if pid and qty and Decimal(str(qty)) > 0]

    if not valid_items:
        flash('Please add at least one item to the sale.', 'danger')
        db.session.rollback()
        return redirect(url_for('sales.new_sale'))

    for pid, qty in valid_items:
        product = Product.query.get(int(pid))
        qty = Decimal(str(qty))

        if qty <= 0:
            continue

        if qty >= product.bulk_limit and product.bulk_limit > 0:
            flash(f'{product.name}: quantity {qty} meets or exceeds bulk limit '
                  f'({product.bulk_limit}). Place a bulk order instead.', 'warning')
            db.session.rollback()
            return redirect(url_for('sales.new_sale'))

        if product.shelf_stock < qty:
            flash(f'Insufficient shelf stock for {product.name}.', 'danger')
            db.session.rollback()
            return redirect(url_for('sales.new_sale'))

        product.shelf_stock -= qty
        line_total = product.selling_price * qty
        subtotal += line_total

        item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=qty,
            unit_price=product.selling_price,
            avco_cost_at_sale=product.avco_cost,
            line_total=line_total
        )
        db.session.add(item)

        movement = StockMovement(
            product_id=product.id,
            movement_type='sale',
            quantity=-qty,
            reference_type='sale',
            reference_id=sale.id,
            created_by_id=current_user.id
        )
        db.session.add(movement)

    tax_amount = subtotal * tax_rate
    total = subtotal + tax_amount

    sale.subtotal = subtotal
    sale.tax_amount = tax_amount
    sale.total = total

    invoice = Invoice(
        invoice_number=generate_invoice_number(),
        sale_id=sale.id,
        issued_by_id=current_user.id
    )
    db.session.add(invoice)

    log('standard', 'sale_created', 'sale', sale.id,
        f'Walk-in sale {sale.sale_number} completed. Total: ¥{total}')

    db.session.commit()
    flash(f'Sale {sale.sale_number} completed. Total: ¥{"{:,.0f}".format(total)}', 'success')
    return redirect(url_for('sales.invoice_detail', id=invoice.id))


# ── Bulk Orders ────────────────────────────────────────────

@sales_bp.route('/bulk-orders')
@login_required
def bulk_orders():
    if not require_permission('manage_bulk_orders'):
        return redirect(url_for('main.dashboard'))
    all_orders = BulkOrder.query.order_by(BulkOrder.id.desc()).all()
    return render_template('sales/bulk_orders.html', orders=all_orders)


@sales_bp.route('/bulk-orders/new', methods=['GET', 'POST'])
@login_required
def new_bulk_order():
    if not require_permission('create_sale'):
        return redirect(url_for('main.dashboard'))
    buyers = BulkBuyer.query.filter_by(is_active=True).order_by(BulkBuyer.full_name).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    return render_template('sales/new_bulk_order.html', buyers=buyers, products=products)


@sales_bp.route('/bulk-orders/process', methods=['POST'])
@login_required
def process_bulk_order():
    if not require_permission('create_sale'):
        return redirect(url_for('main.dashboard'))

    bulk_buyer_id = request.form.get('bulk_buyer_id')
    if not bulk_buyer_id:
        flash('Please select a bulk buyer.', 'danger')
        return redirect(url_for('sales.new_bulk_order'))

    tax_rate = get_tax_rate()
    sale_number = generate_sale_number()

    sale = Sale(
        sale_number=sale_number,
        sale_type='bulk_order',
        bulk_buyer_id=int(bulk_buyer_id),
        status='Completed',
        tax_rate=tax_rate,
        created_by_id=current_user.id
    )
    db.session.add(sale)
    db.session.flush()

    subtotal = Decimal('0')
    product_ids = request.form.getlist('product_id')
    quantities = request.form.getlist('quantity')

    valid_items = [(pid, qty) for pid, qty in zip(product_ids, quantities)
                if pid and qty and Decimal(str(qty)) > 0]

    if not valid_items:
        flash('Please add at least one item to the bulk order.', 'danger')
        db.session.rollback()
        return redirect(url_for('sales.new_bulk_order'))

    for pid, qty in valid_items:
        product = Product.query.get(int(pid))
        qty = Decimal(str(qty))

        if qty <= 0:
            continue

        if product.warehouse_stock < qty:
            flash(f'Insufficient warehouse stock for {product.name}.', 'danger')
            db.session.rollback()
            return redirect(url_for('sales.new_bulk_order'))

        product.warehouse_stock -= qty
        line_total = product.selling_price * qty
        subtotal += line_total

        item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=qty,
            unit_price=product.selling_price,
            avco_cost_at_sale=product.avco_cost,
            line_total=line_total
        )
        db.session.add(item)

        movement = StockMovement(
            product_id=product.id,
            movement_type='sale',
            quantity=-qty,
            reference_type='sale',
            reference_id=sale.id,
            created_by_id=current_user.id
        )
        db.session.add(movement)

    tax_amount = subtotal * tax_rate
    total = subtotal + tax_amount

    sale.subtotal = subtotal
    sale.tax_amount = tax_amount
    sale.total = total

    bulk_order = BulkOrder(
        sale_id=sale.id,
        delivery_status='Pending'
    )
    db.session.add(bulk_order)

    invoice = Invoice(
        invoice_number=generate_invoice_number(),
        sale_id=sale.id,
        issued_by_id=current_user.id
    )
    db.session.add(invoice)

    log('standard', 'sale_created', 'sale', sale.id,
        f'Bulk order {sale.sale_number} created. Total: ¥{total}')

    db.session.commit()
    flash(f'Bulk order {sale.sale_number} placed. Total: ¥{"{:,.0f}".format(total)}',
          'success')
    return redirect(url_for('sales.invoice_detail', id=invoice.id))


@sales_bp.route('/bulk-orders/<int:id>/update-delivery', methods=['POST'])
@login_required
def update_delivery(id):
    if not require_permission('manage_bulk_orders'):
        return redirect(url_for('main.dashboard'))
    bulk_order = BulkOrder.query.get_or_404(id)
    form = DeliveryStatusForm()
    if form.validate_on_submit():
        bulk_order.delivery_status = form.delivery_status.data
        bulk_order.estimated_days = form.estimated_days.data
        if form.delivery_status.data == 'Dispatched':
            bulk_order.dispatched_by_id = current_user.id
            bulk_order.dispatched_at = datetime.datetime.utcnow()
        if form.delivery_status.data == 'Delivered':
            bulk_order.delivered_at = datetime.datetime.utcnow()
        log('standard', 'delivery_status_updated', 'bulk_order', bulk_order.id,
            f'Delivery status updated to {bulk_order.delivery_status}.')
        db.session.commit()
        flash('Delivery status updated.', 'success')
    return redirect(url_for('sales.bulk_orders'))


# ── Transfer Requests ──────────────────────────────────────

@sales_bp.route('/transfer-requests')
@login_required
def transfer_requests():
    if not require_permission('create_transfer_request'):
        return redirect(url_for('main.dashboard'))
    my_requests = StockTransferRequest.query.filter_by(
        requested_by_id=current_user.id
    ).order_by(StockTransferRequest.requested_at.desc()).all()
    form = TransferRequestForm()
    form.product_id.choices = [(p.id, f'{p.sku} — {p.name}')
                                for p in Product.query.filter_by(is_active=True).all()]
    return render_template('sales/transfer_requests.html',
                           requests=my_requests, form=form)


@sales_bp.route('/transfer-requests/add', methods=['POST'])
@login_required
def add_transfer_request():
    if not require_permission('create_transfer_request'):
        return redirect(url_for('main.dashboard'))
    form = TransferRequestForm()
    form.product_id.choices = [(p.id, f'{p.sku} — {p.name}')
                                for p in Product.query.filter_by(is_active=True).all()]
    
    if form.quantity.data <= 0:
        flash('Quantity must be greater than zero.', 'danger')
        return redirect(url_for('sales.transfer_requests'))
    
    if form.validate_on_submit():
        transfer = StockTransferRequest(
            product_id=form.product_id.data,
            quantity=form.quantity.data,
            requested_by_id=current_user.id
        )
        db.session.add(transfer)
        db.session.flush()
        log('standard', 'transfer_request_created', 'stock_transfer_request',
            transfer.id,
            f'Transfer request created for {transfer.quantity} units of '
            f'product {transfer.product_id}.')
        db.session.commit()
        flash('Transfer request submitted to warehouse.', 'success')
    return redirect(url_for('sales.transfer_requests'))


# ── Customer Returns ───────────────────────────────────────

@sales_bp.route('/returns')
@login_required
def customer_returns():
    if not require_permission('manage_customer_returns'):
        return redirect(url_for('main.dashboard'))
    all_returns = CustomerReturn.query.order_by(
        CustomerReturn.created_at.desc()).all()
    form = CustomerReturnForm()
    form.sale_id.choices = [(s.id, s.sale_number)
                             for s in Sale.query.filter_by(
                                 status='Completed').order_by(Sale.id.desc()).all()]
    form.product_id.choices = [(p.id, f'{p.sku} — {p.name}')
                                for p in Product.query.filter_by(is_active=True).all()]
    return render_template('sales/customer_returns.html',
                           returns=all_returns, form=form)


@sales_bp.route('/returns/add', methods=['POST'])
@login_required
def add_customer_return():
    if not require_permission('manage_customer_returns'):
        return redirect(url_for('main.dashboard'))
    form = CustomerReturnForm()
    form.sale_id.choices = [(s.id, s.sale_number)
                             for s in Sale.query.filter_by(
                                 status='Completed').order_by(Sale.id.desc()).all()]
    form.product_id.choices = [(p.id, f'{p.sku} — {p.name}')
                                for p in Product.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        ret = CustomerReturn(
            sale_id=form.sale_id.data,
            product_id=form.product_id.data,
            quantity=form.quantity.data,
            reason=form.reason.data,
            created_by_id=current_user.id
        )
        db.session.add(ret)
        db.session.flush()
        log('standard', 'customer_return_initiated', 'customer_return', ret.id,
            f'Customer return initiated for {ret.quantity} units.')
        db.session.commit()
        flash('Customer return created.', 'success')
    return redirect(url_for('sales.customer_returns'))


@sales_bp.route('/returns/<int:id>/complete', methods=['POST'])
@login_required
def complete_customer_return(id):
    if not require_permission('manage_customer_returns'):
        return redirect(url_for('main.dashboard'))
    ret = CustomerReturn.query.get_or_404(id)
    if ret.status != 'Pending':
        flash('This return has already been completed.', 'danger')
        return redirect(url_for('sales.customer_returns'))

    product = Product.query.get(ret.product_id)
    product.shelf_stock = (product.shelf_stock or Decimal('0')) + ret.quantity

    movement = StockMovement(
        product_id=product.id,
        movement_type='return',
        quantity=ret.quantity,
        reference_type='customer_return',
        reference_id=ret.id,
        created_by_id=current_user.id
    )
    db.session.add(movement)

    ret.status = 'Completed'
    ret.completed_at = datetime.datetime.utcnow()
    ret.completed_by_id = current_user.id

    log('standard', 'customer_return_completed', 'customer_return', ret.id,
        f'Customer return {ret.id} completed. {ret.quantity} units returned to shelf.')
    db.session.commit()
    flash('Return completed. Stock returned to shelf.', 'success')
    return redirect(url_for('sales.customer_returns'))


# ── Invoices ───────────────────────────────────────────────

@sales_bp.route('/invoices')
@login_required
def invoices():
    if not require_permission('view_invoices'):
        return redirect(url_for('main.dashboard'))
    all_invoices = Invoice.query.order_by(Invoice.issued_at.desc()).all()
    return render_template('sales/invoices.html', invoices=all_invoices)


@sales_bp.route('/invoices/<int:id>')
@login_required
def invoice_detail(id):
    if not require_permission('view_invoices'):
        return redirect(url_for('main.dashboard'))
    invoice = Invoice.query.get_or_404(id)
    return render_template('sales/invoice_detail.html', invoice=invoice)