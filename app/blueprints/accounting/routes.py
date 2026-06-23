from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from decimal import Decimal
from app.extensions import db
from app.models.accounting import (LedgerEntry, AccountsPayable,
                                    AccountsReceivable, Payment, TaxEntry)
from app.models.procurement import Supplier, PurchaseOrder
from app.models.sales import BulkBuyer, Sale
from app.models.admin import Currency
from app.models.audit import AuditLog
from . import accounting_bp
from .forms import (LedgerEntryForm, AccountsPayableForm,
                    AccountsReceivableForm, PaymentForm, TaxEntryForm)
import datetime


def log(tier, action, entity_type, entity_id, description,
        old_value=None, new_value=None):
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


# ── Ledger ─────────────────────────────────────────────────

@accounting_bp.route('/ledger')
@login_required
def ledger():
    if not require_permission('view_ledger'):
        return redirect(url_for('main.dashboard'))
    entries = LedgerEntry.query.order_by(
        LedgerEntry.created_at.desc()).limit(200).all()
    form = LedgerEntryForm()
    form.currency_id.choices = [(c.id, f'{c.code} — {c.name}')
                                 for c in Currency.query.filter_by(
                                     is_active=True).all()]
    return render_template('accounting/ledger.html', entries=entries, form=form)


@accounting_bp.route('/ledger/add', methods=['POST'])
@login_required
def add_ledger_entry():
    if not require_permission('edit_ledger'):
        return redirect(url_for('main.dashboard'))
    form = LedgerEntryForm()
    form.currency_id.choices = [(c.id, f'{c.code} — {c.name}')
                                 for c in Currency.query.filter_by(
                                     is_active=True).all()]
    if form.validate_on_submit():
        entry = LedgerEntry(
            entry_type=form.entry_type.data,
            description=form.description.data,
            amount=form.amount.data,
            currency_id=form.currency_id.data,
            exchange_rate=form.exchange_rate.data,
            is_manual=form.is_manual.data,
            created_by_id=current_user.id
        )
        db.session.add(entry)
        db.session.flush()
        log('critical', 'ledger_entry_manual', 'ledger_entry', entry.id,
            f'Manual ledger entry added: {entry.description}',
            None, str(entry.amount))
        db.session.commit()
        flash('Ledger entry added.', 'success')
    return redirect(url_for('accounting.ledger'))


@accounting_bp.route('/ledger/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_ledger_entry(id):
    if not require_permission('edit_ledger'):
        return redirect(url_for('main.dashboard'))
    entry = LedgerEntry.query.get_or_404(id)
    form = LedgerEntryForm(obj=entry)
    form.currency_id.choices = [(c.id, f'{c.code} — {c.name}')
                                 for c in Currency.query.filter_by(
                                     is_active=True).all()]
    if form.validate_on_submit():
        old = f'{entry.entry_type}: {entry.amount}'
        entry.entry_type = form.entry_type.data
        entry.description = form.description.data
        entry.amount = form.amount.data
        entry.currency_id = form.currency_id.data
        entry.exchange_rate = form.exchange_rate.data
        entry.is_manual = True
        new = f'{entry.entry_type}: {entry.amount}'
        log('critical', 'ledger_entry_edited', 'ledger_entry', entry.id,
            f'Ledger entry {entry.id} manually edited.', old, new)
        db.session.commit()
        flash('Ledger entry updated.', 'success')
        return redirect(url_for('accounting.ledger'))
    return render_template('accounting/edit_ledger_entry.html',
                           form=form, entry=entry)


# ── Accounts Payable ───────────────────────────────────────

@accounting_bp.route('/payables')
@login_required
def payables():
    if not require_permission('manage_payables'):
        return redirect(url_for('main.dashboard'))
    all_payables = AccountsPayable.query.order_by(
        AccountsPayable.created_at.desc()).all()
    form = AccountsPayableForm()
    form.supplier_id.choices = [(s.id, s.name)
                                 for s in Supplier.query.filter_by(
                                     is_active=True).all()]
    form.po_id.choices = [(0, '— None —')] + [
        (p.id, p.po_number) for p in PurchaseOrder.query.filter_by(
            status='Goods Received').all()
    ]
    form.currency_id.choices = [(c.id, f'{c.code} — {c.name}')
                                 for c in Currency.query.filter_by(
                                     is_active=True).all()]
    return render_template('accounting/payables.html',
                           payables=all_payables, form=form)


@accounting_bp.route('/payables/add', methods=['POST'])
@login_required
def add_payable():
    if not require_permission('manage_payables'):
        return redirect(url_for('main.dashboard'))
    form = AccountsPayableForm()
    form.supplier_id.choices = [(s.id, s.name)
                                 for s in Supplier.query.filter_by(
                                     is_active=True).all()]
    form.po_id.choices = [(0, '— None —')] + [
        (p.id, p.po_number) for p in PurchaseOrder.query.filter_by(
            status='Goods Received').all()
    ]
    form.currency_id.choices = [(c.id, f'{c.code} — {c.name}')
                                 for c in Currency.query.filter_by(
                                     is_active=True).all()]
    if form.validate_on_submit():
        po_id = form.po_id.data if form.po_id.data != 0 else None
        payable = AccountsPayable(
            supplier_id=form.supplier_id.data,
            po_id=po_id,
            amount_due=form.amount_due.data,
            currency_id=form.currency_id.data,
            exchange_rate=form.exchange_rate.data,
            due_date=form.due_date.data,
            created_by_id=current_user.id
        )
        db.session.add(payable)
        db.session.commit()
        flash('Payable recorded.', 'success')
    return redirect(url_for('accounting.payables'))


# ── Accounts Receivable ────────────────────────────────────

@accounting_bp.route('/receivables')
@login_required
def receivables():
    if not require_permission('manage_receivables'):
        return redirect(url_for('main.dashboard'))
    all_receivables = AccountsReceivable.query.order_by(
        AccountsReceivable.created_at.desc()).all()
    form = AccountsReceivableForm()
    form.bulk_buyer_id.choices = [(b.id, b.full_name)
                                   for b in BulkBuyer.query.filter_by(
                                       is_active=True).all()]
    form.sale_id.choices = [(0, '— None —')] + [
        (s.id, s.sale_number) for s in Sale.query.filter_by(
            sale_type='bulk_order', status='Completed').all()
    ]
    return render_template('accounting/receivables.html',
                           receivables=all_receivables, form=form)


@accounting_bp.route('/receivables/add', methods=['POST'])
@login_required
def add_receivable():
    if not require_permission('manage_receivables'):
        return redirect(url_for('main.dashboard'))
    form = AccountsReceivableForm()
    form.bulk_buyer_id.choices = [(b.id, b.full_name)
                                   for b in BulkBuyer.query.filter_by(
                                       is_active=True).all()]
    form.sale_id.choices = [(0, '— None —')] + [
        (s.id, s.sale_number) for s in Sale.query.filter_by(
            sale_type='bulk_order', status='Completed').all()
    ]
    if form.validate_on_submit():
        sale_id = form.sale_id.data if form.sale_id.data != 0 else None
        receivable = AccountsReceivable(
            bulk_buyer_id=form.bulk_buyer_id.data,
            sale_id=sale_id,
            amount_due=form.amount_due.data,
            due_date=form.due_date.data,
            created_by_id=current_user.id
        )
        db.session.add(receivable)
        db.session.commit()
        flash('Receivable recorded.', 'success')
    return redirect(url_for('accounting.receivables'))


# ── Payments ───────────────────────────────────────────────

@accounting_bp.route('/payments')
@login_required
def payments():
    if not require_permission('record_payments'):
        return redirect(url_for('main.dashboard'))
    all_payments = Payment.query.order_by(Payment.payment_date.desc()).all()
    form = PaymentForm()
    form.currency_id.choices = [(c.id, f'{c.code} — {c.name}')
                                 for c in Currency.query.filter_by(
                                     is_active=True).all()]
    form.payable_id.choices = [(0, '— None —')] + [
        (p.id, f'{p.supplier.name} — ¥{p.amount_due}')
        for p in AccountsPayable.query.filter(
            AccountsPayable.status != 'Paid').all()
    ]
    form.receivable_id.choices = [(0, '— None —')] + [
        (r.id, f'{r.bulk_buyer.full_name} — ¥{r.amount_due}')
        for r in AccountsReceivable.query.filter(
            AccountsReceivable.status != 'Paid').all()
    ]
    return render_template('accounting/payments.html',
                           payments=all_payments, form=form)


@accounting_bp.route('/payments/add', methods=['POST'])
@login_required
def add_payment():
    if not require_permission('record_payments'):
        return redirect(url_for('main.dashboard'))
    form = PaymentForm()
    form.currency_id.choices = [(c.id, f'{c.code} — {c.name}')
                                 for c in Currency.query.filter_by(
                                     is_active=True).all()]
    form.payable_id.choices = [(0, '— None —')] + [
        (p.id, f'{p.supplier.name} — ¥{p.amount_due}')
        for p in AccountsPayable.query.filter(
            AccountsPayable.status != 'Paid').all()
    ]
    form.receivable_id.choices = [(0, '— None —')] + [
        (r.id, f'{r.bulk_buyer.full_name} — ¥{r.amount_due}')
        for r in AccountsReceivable.query.filter(
            AccountsReceivable.status != 'Paid').all()
    ]
    if form.validate_on_submit():
        payable_id = form.payable_id.data if form.payable_id.data != 0 else None
        receivable_id = form.receivable_id.data \
            if form.receivable_id.data != 0 else None

        payment = Payment(
            payment_type=form.payment_type.data,
            payable_id=payable_id,
            receivable_id=receivable_id,
            amount=form.amount.data,
            currency_id=form.currency_id.data,
            exchange_rate=form.exchange_rate.data,
            payment_date=form.payment_date.data,
            notes=form.notes.data,
            created_by_id=current_user.id
        )
        db.session.add(payment)

        if payable_id:
            payable = AccountsPayable.query.get(payable_id)
            payable.amount_paid = (payable.amount_paid or Decimal('0')) \
                + form.amount.data
            if payable.amount_paid >= payable.amount_due:
                payable.status = 'Paid'
            else:
                payable.status = 'Partial'

        if receivable_id:
            receivable = AccountsReceivable.query.get(receivable_id)
            receivable.amount_paid = (receivable.amount_paid or Decimal('0')) \
                + form.amount.data
            if receivable.amount_paid >= receivable.amount_due:
                receivable.status = 'Paid'
            else:
                receivable.status = 'Partial'

        log('critical', 'payment_recorded', 'payment', None,
            f'{form.payment_type.data} payment of {form.amount.data} recorded.')
        db.session.commit()
        flash('Payment recorded.', 'success')
    return redirect(url_for('accounting.payments'))


# ── Tax Entries ────────────────────────────────────────────

@accounting_bp.route('/tax')
@login_required
def tax_entries():
    if not require_permission('manage_tax_entries'):
        return redirect(url_for('main.dashboard'))
    entries = TaxEntry.query.order_by(TaxEntry.created_at.desc()).all()
    form = TaxEntryForm()
    collected_total = sum(e.amount for e in entries if e.tax_type == 'collected')
    paid_total = sum(e.amount for e in entries if e.tax_type == 'paid')
    return render_template('accounting/tax.html', entries=entries, form=form,
                           collected_total=collected_total, paid_total=paid_total)


@accounting_bp.route('/tax/add', methods=['POST'])
@login_required
def add_tax_entry():
    if not require_permission('manage_tax_entries'):
        return redirect(url_for('main.dashboard'))
    form = TaxEntryForm()
    if form.validate_on_submit():
        entry = TaxEntry(
            tax_type=form.tax_type.data,
            amount=form.amount.data,
            tax_rate=form.tax_rate.data,
            reference_type=form.reference_type.data or None,
            reference_id=int(form.reference_id.data)
            if form.reference_id.data else None,
            created_by_id=current_user.id
        )
        db.session.add(entry)
        db.session.commit()
        flash('Tax entry recorded.', 'success')
    return redirect(url_for('accounting.tax_entries'))