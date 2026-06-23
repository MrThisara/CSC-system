from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from decimal import Decimal
from app.extensions import db
from app.models.procurement import Product
from app.models.warehouse import StockWriteOff, StockMovement, StockTransferRequest
from app.models.audit import AuditLog
from . import warehouse_bp
from .forms import WriteOffForm, TransferReviewForm
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


# ── Inventory ──────────────────────────────────────────────

@warehouse_bp.route('/inventory')
@login_required
def inventory():
    if not require_permission('view_inventory'):
        return redirect(url_for('main.dashboard'))
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    return render_template('warehouse/inventory.html', products=products)


# ── Transfer Requests ──────────────────────────────────────

@warehouse_bp.route('/transfers')
@login_required
def transfers():
    if not require_permission('approve_transfers'):
        return redirect(url_for('main.dashboard'))
    pending = StockTransferRequest.query.filter_by(
        status='Pending').order_by(StockTransferRequest.requested_at.desc()).all()
    completed = StockTransferRequest.query.filter(
        StockTransferRequest.status != 'Pending'
    ).order_by(StockTransferRequest.reviewed_at.desc()).limit(50).all()
    form = TransferReviewForm()
    return render_template('warehouse/transfers.html',
                           pending=pending, completed=completed, form=form)


@warehouse_bp.route('/transfers/<int:id>/approve', methods=['POST'])
@login_required
def approve_transfer(id):
    if not require_permission('approve_transfers'):
        return redirect(url_for('main.dashboard'))
    transfer = StockTransferRequest.query.get_or_404(id)
    if transfer.status != 'Pending':
        flash('This request has already been reviewed.', 'danger')
        return redirect(url_for('warehouse.transfers'))

    product = Product.query.get(transfer.product_id)
    if product.warehouse_stock < transfer.quantity:
        flash('Insufficient warehouse stock to fulfill this transfer.', 'danger')
        return redirect(url_for('warehouse.transfers'))

    product.warehouse_stock = (product.warehouse_stock or Decimal('0')) - transfer.quantity
    product.shelf_stock = (product.shelf_stock or Decimal('0')) + transfer.quantity

    movement = StockMovement(
        product_id=product.id,
        movement_type='transfer_out',
        quantity=transfer.quantity,
        reference_type='transfer_request',
        reference_id=transfer.id,
        created_by_id=current_user.id
    )
    db.session.add(movement)

    transfer.status = 'Approved'
    transfer.reviewed_by_id = current_user.id
    transfer.reviewed_at = datetime.datetime.utcnow()

    log('standard', 'transfer_approved', 'stock_transfer_request', transfer.id,
        f'Transfer of {transfer.quantity} units of {product.name} approved.')
    log('standard', 'stock_movement_executed', 'product', product.id,
        f'Stock moved from warehouse to shelf: {transfer.quantity} units of {product.name}.')

    db.session.commit()
    flash(f'Transfer approved. {transfer.quantity} units moved to shelf.', 'success')
    return redirect(url_for('warehouse.transfers'))


@warehouse_bp.route('/transfers/<int:id>/reject', methods=['POST'])
@login_required
def reject_transfer(id):
    if not require_permission('approve_transfers'):
        return redirect(url_for('main.dashboard'))
    transfer = StockTransferRequest.query.get_or_404(id)
    if transfer.status != 'Pending':
        flash('This request has already been reviewed.', 'danger')
        return redirect(url_for('warehouse.transfers'))

    reason = request.form.get('rejection_reason', '')
    transfer.status = 'Rejected'
    transfer.rejection_reason = reason
    transfer.reviewed_by_id = current_user.id
    transfer.reviewed_at = datetime.datetime.utcnow()

    log('standard', 'transfer_rejected', 'stock_transfer_request', transfer.id,
        f'Transfer request {transfer.id} rejected. Reason: {reason}')

    db.session.commit()
    flash('Transfer request rejected.', 'warning')
    return redirect(url_for('warehouse.transfers'))


# ── Write-offs ─────────────────────────────────────────────

@warehouse_bp.route('/write-offs', methods=['GET', 'POST'])
@login_required
def write_offs():
    if not require_permission('write_off_stock'):
        return redirect(url_for('main.dashboard'))
    form = WriteOffForm()
    form.product_id.choices = [(p.id, f'{p.sku} — {p.name}')
                                for p in Product.query.filter_by(is_active=True).all()]
    all_writeoffs = StockWriteOff.query.order_by(
        StockWriteOff.written_off_at.desc()).all()

    if form.validate_on_submit():
        if form.quantity.data <= 0:
            flash('Quantity must be grater than zero', 'danger')
            return redirect(url_for('warehouse.write_offs'))
        
        product = Product.query.get(form.product_id.data)
        qty = Decimal(str(form.quantity.data))

        if product.warehouse_stock < qty:
            flash('Quantity exceeds current warehouse stock.', 'danger')
            return redirect(url_for('warehouse.write_offs'))

        old_stock = str(product.warehouse_stock)
        product.warehouse_stock = (product.warehouse_stock or Decimal('0')) - qty

        writeoff = StockWriteOff(
            product_id=product.id,
            quantity=qty,
            reason=form.reason.data,
            written_off_by_id=current_user.id
        )
        db.session.add(writeoff)
        db.session.flush()

        movement = StockMovement(
            product_id=product.id,
            movement_type='write_off',
            quantity=-qty,
            reference_type='stock_write_off',
            reference_id=writeoff.id,
            created_by_id=current_user.id
        )
        db.session.add(movement)

        log('standard', 'stock_written_off', 'product', product.id,
            f'{qty} units of {product.name} written off.',
            old_stock, str(product.warehouse_stock))

        db.session.commit()
        flash(f'{qty} units of {product.name} written off.', 'success')
        return redirect(url_for('warehouse.write_offs'))

    return render_template('warehouse/write_offs.html',
                           form=form, write_offs=all_writeoffs)


# ── Stock Movements Log ────────────────────────────────────

@warehouse_bp.route('/movements')
@login_required
def movements():
    if not require_permission('view_inventory'):
        return redirect(url_for('main.dashboard'))
    all_movements = StockMovement.query.order_by(
        StockMovement.created_at.desc()).limit(200).all()
    return render_template('warehouse/movements.html', movements=all_movements)