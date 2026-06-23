from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from decimal import Decimal
from app.extensions import db
from app.models.procurement import (Supplier, Product, PurchaseOrder, PurchaseOrderItem,
                                     Shipment, LandedCost, LandedCostAllocation, SupplierReturn)
from app.models.admin import Currency, UnitOfMeasurement
from app.models.warehouse import StockMovement
from app.models.audit import AuditLog
from . import procurement_bp
from .forms import (SupplierForm, ProductForm, PurchaseOrderForm, POItemForm,
                    ShipmentForm, LandedCostForm, SupplierReturnForm)
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


def generate_po_number():
    year = datetime.datetime.now().year
    last = PurchaseOrder.query.filter(
        PurchaseOrder.po_number.like(f'PO-{year}-%')
    ).order_by(PurchaseOrder.id.desc()).first()
    if last:
        last_num = int(last.po_number.split('-')[-1])
        return f'PO-{year}-{str(last_num + 1).zfill(4)}'
    return f'PO-{year}-0001'


def recalculate_avco(product, new_quantity, new_unit_cost_jpy):
    old_avco = product.avco_cost or Decimal('0')
    old_stock = product.warehouse_stock or Decimal('0')
    new_quantity = Decimal(str(new_quantity))
    new_unit_cost_jpy = Decimal(str(new_unit_cost_jpy))

    if old_stock + new_quantity == 0:
        return old_avco

    new_avco = ((old_stock * old_avco) + (new_quantity * new_unit_cost_jpy)) / (old_stock + new_quantity)
    return round(new_avco, 4)


# ── Suppliers ──────────────────────────────────────────────

@procurement_bp.route('/suppliers')
@login_required
def suppliers():
    if not require_permission('manage_suppliers'):
        return redirect(url_for('main.dashboard'))
    all_suppliers = Supplier.query.order_by(Supplier.name).all()
    form = SupplierForm()
    form.currency_id.choices = [(c.id, f'{c.code} — {c.name}')
                                 for c in Currency.query.filter_by(is_active=True).all()]
    return render_template('procurement/suppliers.html', suppliers=all_suppliers, form=form)


@procurement_bp.route('/suppliers/add', methods=['POST'])
@login_required
def add_supplier():
    if not require_permission('manage_suppliers'):
        return redirect(url_for('main.dashboard'))
    form = SupplierForm()
    form.currency_id.choices = [(c.id, f'{c.code} — {c.name}')
                                 for c in Currency.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        existing = Supplier.query.filter_by(name=form.name.data).first()
        if existing:
            flash(f'Supplier {form.name.data} already exists', 'danger')
            return redirect(url_for('procurement.suppliers'))
        supplier = Supplier(
            name=form.name.data,
            contact_name=form.contact_name.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,
            country=form.country.data,
            lead_time_days=form.lead_time_days.data,
            currency_id=form.currency_id.data,
            created_by_id=current_user.id
        )
        db.session.add(supplier)
        db.session.flush()
        log('standard', 'supplier_created', 'supplier', supplier.id,
            f'Supplier {supplier.name} created.')
        db.session.commit()
        flash(f'Supplier {supplier.name} added.', 'success')
    return redirect(url_for('procurement.suppliers'))


@procurement_bp.route('/suppliers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_supplier(id):
    if not require_permission('manage_suppliers'):
        return redirect(url_for('main.dashboard'))
    supplier = Supplier.query.get_or_404(id)
    form = SupplierForm(obj=supplier)
    form.currency_id.choices = [(c.id, f'{c.code} — {c.name}')
                                 for c in Currency.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        supplier.name = form.name.data
        supplier.contact_name = form.contact_name.data
        supplier.email = form.email.data
        supplier.phone = form.phone.data
        supplier.address = form.address.data
        supplier.country = form.country.data
        supplier.lead_time_days = form.lead_time_days.data
        supplier.currency_id = form.currency_id.data
        log('standard', 'supplier_edited', 'supplier', supplier.id,
            f'Supplier {supplier.name} edited.')
        db.session.commit()
        flash(f'Supplier {supplier.name} updated.', 'success')
        return redirect(url_for('procurement.suppliers'))
    return render_template('procurement/edit_supplier.html', form=form, supplier=supplier)


# ── Products ───────────────────────────────────────────────

@procurement_bp.route('/products')
@login_required
def products():
    if not require_permission('manage_products'):
        return redirect(url_for('main.dashboard'))
    all_products = Product.query.order_by(Product.name).all()
    form = ProductForm()
    form.unit_id.choices = [(u.id, u.name)
                             for u in UnitOfMeasurement.query.filter_by(is_active=True).all()]
    return render_template('procurement/products.html', products=all_products, form=form)


@procurement_bp.route('/products/add', methods=['POST'])
@login_required
def add_product():
    if not require_permission('manage_products'):
        return redirect(url_for('main.dashboard'))
    form = ProductForm()
    form.unit_id.choices = [(u.id, u.name)
                             for u in UnitOfMeasurement.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        existing = Product.query.filter_by(sku=form.sku.data).first()
        if existing:
            flash(f'SKU {form.sku.data} already exists.', 'danger')
            return redirect(url_for('procurement.products'))
        product = Product(
            sku=form.sku.data,
            name=form.name.data,
            description=form.description.data,
            unit_id=form.unit_id.data,
            selling_price=form.selling_price.data,
            warehouse_reorder_threshold=form.warehouse_reorder_threshold.data,
            shelf_reorder_threshold=form.shelf_reorder_threshold.data,
            bulk_limit=form.bulk_limit.data,
            created_by_id=current_user.id
        )
        db.session.add(product)
        db.session.flush()
        log('standard', 'product_created', 'product', product.id,
            f'Product {product.name} created.')
        db.session.commit()
        flash(f'Product {product.name} added.', 'success')
    return redirect(url_for('procurement.products'))


@procurement_bp.route('/products/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    if not require_permission('manage_products'):
        return redirect(url_for('main.dashboard'))
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    form.unit_id.choices = [(u.id, u.name)
                             for u in UnitOfMeasurement.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        existing = Product.query.filter(
            Product.sku == form.sku.data,
            Product.id != product.id
        ).first()
        if existing:
            flash(f'SKU {form.sku.data} is already used by another product.','danger')
            return render_template('procurement/edit_product.html',
                                   form=form, product=product)
        product.sku = form.sku.data
        product.name = form.name.data
        product.description = form.description.data
        product.unit_id = form.unit_id.data
        product.selling_price = form.selling_price.data
        product.warehouse_reorder_threshold = form.warehouse_reorder_threshold.data
        product.shelf_reorder_threshold = form.shelf_reorder_threshold.data
        product.bulk_limit = form.bulk_limit.data
        log('standard', 'product_edited', 'product', product.id,
            f'Product {product.name} edited.')
        db.session.commit()
        flash(f'Product {product.name} updated.', 'success')
        return redirect(url_for('procurement.products'))
    return render_template('procurement/edit_product.html', form=form, product=product)


# ── Purchase Orders ────────────────────────────────────────

@procurement_bp.route('/purchase-orders')
@login_required
def purchase_orders():
    if not require_permission('create_po'):
        return redirect(url_for('main.dashboard'))
    all_pos = PurchaseOrder.query.order_by(PurchaseOrder.created_at.desc()).all()
    return render_template('procurement/purchase_orders.html', purchase_orders=all_pos)


@procurement_bp.route('/purchase-orders/new', methods=['GET', 'POST'])
@login_required
def new_purchase_order():
    if not require_permission('create_po'):
        return redirect(url_for('main.dashboard'))
    form = PurchaseOrderForm()
    form.supplier_id.choices = [(s.id, s.name)
                                 for s in Supplier.query.filter_by(is_active=True).all()]
    form.currency_id.choices = [(c.id, f'{c.code} — {c.name}')
                                 for c in Currency.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        po = PurchaseOrder(
            po_number=generate_po_number(),
            supplier_id=form.supplier_id.data,
            currency_id=form.currency_id.data,
            exchange_rate=form.exchange_rate.data,
            expected_delivery=form.expected_delivery.data,
            notes=form.notes.data,
            status='Draft',
            created_by_id=current_user.id
        )
        db.session.add(po)
        db.session.flush()
        log('standard', 'po_created', 'purchase_order', po.id,
            f'Purchase order {po.po_number} created.')
        db.session.commit()
        flash(f'Purchase order {po.po_number} created.', 'success')
        return redirect(url_for('procurement.po_detail', id=po.id))
    return render_template('procurement/new_po.html', form=form)


@procurement_bp.route('/purchase-orders/<int:id>')
@login_required
def po_detail(id):
    if not require_permission('create_po'):
        return redirect(url_for('main.dashboard'))
    po = PurchaseOrder.query.get_or_404(id)
    item_form = POItemForm()
    item_form.product_id.choices = [(p.id, f'{p.sku} — {p.name}')
                                     for p in Product.query.filter_by(is_active=True).all()]
    return render_template('procurement/po_detail.html', po=po, item_form=item_form)


@procurement_bp.route('/purchase-orders/<int:id>/add-item', methods=['POST'])
@login_required
def add_po_item(id):
    if not require_permission('create_po'):
        return redirect(url_for('main.dashboard'))
    po = PurchaseOrder.query.get_or_404(id)
    if po.status != 'Draft':
        flash('Cannot modify a purchase order that is no longer in Draft status.', 'danger')
        return redirect(url_for('procurement.po_detail', id=id))
    form = POItemForm()
    form.product_id.choices = [(p.id, f'{p.sku} — {p.name}')
                                for p in Product.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        existing_item = PurchaseOrderItem.query.filter_by(
            po_id=po.id,
            product_id=form.product_id.data
        ).first()
        if existing_item:
            flash('This product is already on the purchase order.', 'danger')
            return redirect(url_for('procurement.po_detail', id=id))
        item = PurchaseOrderItem(
            po_id=po.id,
            product_id=form.product_id.data,
            quantity=form.quantity.data,
            unit_price=form.unit_price.data
        )
        db.session.add(item)
        db.session.commit()
        flash('Item added to purchase order.', 'success')
    return redirect(url_for('procurement.po_detail', id=id))


@procurement_bp.route('/purchase-orders/<int:id>/submit', methods=['POST'])
@login_required
def submit_po(id):
    if not require_permission('create_po'):
        return redirect(url_for('main.dashboard'))
    po = PurchaseOrder.query.get_or_404(id)
    if po.status != 'Draft':
        flash('Only Draft purchase orders can be submitted.', 'danger')
        return redirect(url_for('procurement.po_detail', id=id))
    if po.items.count() == 0:
        flash('Cannot submit a purchase order with no items.', 'danger')
        return redirect(url_for('procurement.po_detail', id=id))
    po.status = 'Submitted'
    po.submitted_at = datetime.datetime.utcnow()
    log('standard', 'po_submitted', 'purchase_order', po.id,
        f'Purchase order {po.po_number} submitted for approval.')
    db.session.commit()
    flash(f'Purchase order {po.po_number} submitted for CEO approval.', 'success')
    return redirect(url_for('procurement.po_detail', id=id))


@procurement_bp.route('/purchase-orders/<int:id>/approve', methods=['POST'])
@login_required
def approve_po(id):
    if not require_permission('approve_po'):
        return redirect(url_for('main.dashboard'))
    po = PurchaseOrder.query.get_or_404(id)
    if po.status != 'Submitted':
        flash('Only submitted purchase orders can be approved.', 'danger')
        return redirect(url_for('procurement.po_detail', id=id))
    po.status = 'Approved'
    po.approved_at = datetime.datetime.utcnow()
    po.approved_by_id = current_user.id
    log('critical', 'po_approved', 'purchase_order', po.id,
        f'Purchase order {po.po_number} approved.', 'Submitted', 'Approved')
    db.session.commit()
    flash(f'Purchase order {po.po_number} approved.', 'success')
    return redirect(url_for('procurement.po_detail', id=id))


@procurement_bp.route('/purchase-orders/<int:id>/reject', methods=['POST'])
@login_required
def reject_po(id):
    if not require_permission('approve_po'):
        return redirect(url_for('main.dashboard'))
    po = PurchaseOrder.query.get_or_404(id)
    if po.status != 'Submitted':
        flash('Only submitted purchase orders can be rejected.', 'danger')
        return redirect(url_for('procurement.po_detail', id=id))
    reason = request.form.get('rejection_reason', '')
    po.status = 'Rejected'
    po.rejection_reason = reason
    po.approved_by_id = current_user.id
    log('critical', 'po_rejected', 'purchase_order', po.id,
        f'Purchase order {po.po_number} rejected. Reason: {reason}',
        'Submitted', 'Rejected')
    db.session.commit()
    flash(f'Purchase order {po.po_number} rejected.', 'warning')
    return redirect(url_for('procurement.po_detail', id=id))


@procurement_bp.route('/purchase-orders/<int:id>/send', methods=['POST'])
@login_required
def send_po(id):
    if not require_permission('send_po'):
        return redirect(url_for('main.dashboard'))
    po = PurchaseOrder.query.get_or_404(id)
    if po.status != 'Approved':
        flash('Only approved purchase orders can be sent to supplier.', 'danger')
        return redirect(url_for('procurement.po_detail', id=id))
    po.status = 'Sent to Supplier'
    po.sent_at = datetime.datetime.utcnow()
    log('standard', 'po_sent', 'purchase_order', po.id,
        f'Purchase order {po.po_number} sent to supplier.')
    db.session.commit()
    flash(f'Purchase order {po.po_number} marked as sent to supplier.', 'success')
    return redirect(url_for('procurement.po_detail', id=id))


@procurement_bp.route('/purchase-orders/<int:id>/receive', methods=['POST'])
@login_required
def receive_goods(id):
    if not require_permission('receive_goods'):
        return redirect(url_for('main.dashboard'))
    po = PurchaseOrder.query.get_or_404(id)
    if po.status != 'Sent to Supplier':
        flash('Only purchase orders sent to supplier can have goods received.', 'danger')
        return redirect(url_for('procurement.po_detail', id=id))

    exchange_rate = po.exchange_rate or Decimal('1')

    for item in po.items:
        qty_received = request.form.get(f'qty_received_{item.id}')
        if not qty_received:
            continue
        qty_received = Decimal(str(qty_received))
        if qty_received <= 0:
            continue

        item.quantity_received = qty_received
        unit_cost_jpy = item.unit_price * exchange_rate

        old_avco = str(item.product.avco_cost)
        new_avco = recalculate_avco(item.product, qty_received, unit_cost_jpy)

        item.product.avco_cost = new_avco
        item.product.warehouse_stock = (item.product.warehouse_stock or Decimal('0')) + qty_received

        log('critical', 'avco_updated', 'product', item.product.id,
            f'AVCO updated on goods received for {item.product.name}.',
            old_avco, str(new_avco))

        movement = StockMovement(
            product_id=item.product.id,
            movement_type='goods_received',
            quantity=qty_received,
            reference_type='purchase_order',
            reference_id=po.id,
            created_by_id=current_user.id
        )
        db.session.add(movement)

    po.status = 'Goods Received'
    log('critical', 'goods_received', 'purchase_order', po.id,
        f'Goods received for purchase order {po.po_number}.',
        'Sent to Supplier', 'Goods Received')
    db.session.commit()
    flash(f'Goods received for {po.po_number}. Stock and AVCO updated.', 'success')
    return redirect(url_for('procurement.po_detail', id=id))


# ── Shipments ──────────────────────────────────────────────

@procurement_bp.route('/purchase-orders/<int:po_id>/shipments/add', methods=['POST'])
@login_required
def add_shipment(po_id):
    if not require_permission('manage_shipments'):
        return redirect(url_for('main.dashboard'))
    po = PurchaseOrder.query.get_or_404(po_id)
    form = ShipmentForm()
    if form.validate_on_submit():
        shipment = Shipment(
            po_id=po.id,
            tracking_number=form.tracking_number.data,
            carrier=form.carrier.data,
            shipped_date=form.shipped_date.data,
            estimated_arrival=form.estimated_arrival.data,
            notes=form.notes.data
        )
        db.session.add(shipment)
        db.session.commit()
        flash('Shipment added.', 'success')
    return redirect(url_for('procurement.po_detail', id=po_id))


# ── Landed Costs ───────────────────────────────────────────

@procurement_bp.route('/shipments/<int:shipment_id>/landed-cost', methods=['GET', 'POST'])
@login_required
def landed_cost(shipment_id):
    if not require_permission('manage_landed_costs'):
        return redirect(url_for('main.dashboard'))
    shipment = Shipment.query.get_or_404(shipment_id)
    form = LandedCostForm()
    form.currency_id.choices = [(c.id, f'{c.code} — {c.name}')
                                 for c in Currency.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        freight = form.freight.data or Decimal('0')
        duty = form.import_duty.data or Decimal('0')
        insurance = form.insurance.data or Decimal('0')
        other = form.other.data or Decimal('0')
        total = freight + duty + insurance + other

        lc = LandedCost(
            shipment_id=shipment.id,
            freight=freight,
            import_duty=duty,
            insurance=insurance,
            other=other,
            total=total,
            currency_id=form.currency_id.data,
            exchange_rate=form.exchange_rate.data,
            recorded_by_id=current_user.id
        )
        db.session.add(lc)
        db.session.flush()

        items = shipment.purchase_order.items.all()
        total_qty = sum(i.quantity for i in items)

        if total_qty > 0:
            for item in items:
                share = item.quantity / total_qty
                allocated = round(total * share * form.exchange_rate.data, 4)
                allocation = LandedCostAllocation(
                    landed_cost_id=lc.id,
                    product_id=item.product_id,
                    allocated_amount=allocated
                )
                db.session.add(allocation)

        log('standard', 'landed_cost_recorded', 'shipment', shipment.id,
            f'Landed cost recorded for shipment {shipment.id}. Total: {total}')
        db.session.commit()
        flash('Landed cost recorded and allocated.', 'success')
        return redirect(url_for('procurement.po_detail', id=shipment.po_id))

    return render_template('procurement/landed_cost.html', form=form, shipment=shipment)


# ── Supplier Returns ───────────────────────────────────────

@procurement_bp.route('/supplier-returns')
@login_required
def supplier_returns():
    if not require_permission('manage_supplier_returns'):
        return redirect(url_for('main.dashboard'))
    all_returns = SupplierReturn.query.order_by(SupplierReturn.created_at.desc()).all()
    form = SupplierReturnForm()
    form.supplier_id.choices = [(s.id, s.name)
                                 for s in Supplier.query.filter_by(is_active=True).all()]
    form.product_id.choices = [(p.id, f'{p.sku} — {p.name}')
                                for p in Product.query.filter_by(is_active=True).all()]
    return render_template('procurement/supplier_returns.html',
                           returns=all_returns, form=form)


@procurement_bp.route('/supplier-returns/add', methods=['POST'])
@login_required
def add_supplier_return():
    if not require_permission('manage_supplier_returns'):
        return redirect(url_for('main.dashboard'))
    form = SupplierReturnForm()
    form.supplier_id.choices = [(s.id, s.name)
                                 for s in Supplier.query.filter_by(is_active=True).all()]
    form.product_id.choices = [(p.id, f'{p.sku} — {p.name}')
                                for p in Product.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        ret = SupplierReturn(
            supplier_id=form.supplier_id.data,
            product_id=form.product_id.data,
            quantity=form.quantity.data,
            reason=form.reason.data,
            created_by_id=current_user.id
        )
        db.session.add(ret)
        db.session.flush()
        log('standard', 'supplier_return_initiated', 'supplier_return', ret.id,
            f'Supplier return initiated for {ret.quantity} units of product {ret.product_id}.')
        db.session.commit()
        flash('Supplier return created.', 'success')
    return redirect(url_for('procurement.supplier_returns'))


@procurement_bp.route('/supplier-returns/<int:id>/complete', methods=['POST'])
@login_required
def complete_supplier_return(id):
    if not require_permission('manage_supplier_returns'):
        return redirect(url_for('main.dashboard'))
    ret = SupplierReturn.query.get_or_404(id)
    if ret.status != 'Pending':
        flash('This return has already been completed.', 'danger')
        return redirect(url_for('procurement.supplier_returns'))

    product = Product.query.get(ret.product_id)
    product.warehouse_stock = (product.warehouse_stock or Decimal('0')) - ret.quantity

    movement = StockMovement(
        product_id=product.id,
        movement_type='supplier_return',
        quantity=-ret.quantity,
        reference_type='supplier_return',
        reference_id=ret.id,
        created_by_id=current_user.id
    )
    db.session.add(movement)

    ret.status = 'Completed'
    ret.completed_at = datetime.datetime.utcnow()
    ret.completed_by_id = current_user.id

    log('standard', 'supplier_return_completed', 'supplier_return', ret.id,
        f'Supplier return {ret.id} completed. Stock reduced by {ret.quantity}.')
    db.session.commit()
    flash('Supplier return completed. Stock updated.', 'success')
    return redirect(url_for('procurement.supplier_returns'))