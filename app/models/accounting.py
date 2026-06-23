from app.extensions import db
from datetime import datetime


class LedgerEntry(db.Model):
    __tablename__ = 'ledger_entry'

    id = db.Column(db.Integer, primary_key=True)
    entry_type = db.Column(db.String(50), nullable=False)
    # payable / receivable / tax_collected / tax_paid / payment / adjustment

    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    currency_id = db.Column(db.Integer, db.ForeignKey('currency.id'))
    currency = db.relationship('Currency')
    exchange_rate = db.Column(db.Numeric(14, 6))

    reference_id = db.Column(db.Integer)
    reference_type = db.Column(db.String(50))

    is_manual = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')


class AccountsPayable(db.Model):
    __tablename__ = 'accounts_payable'

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    supplier = db.relationship('Supplier', backref='payables')

    po_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'))
    purchase_order = db.relationship('PurchaseOrder', backref='payable')

    amount_due = db.Column(db.Numeric(14, 2), nullable=False)
    amount_paid = db.Column(db.Numeric(14, 2), default=0)
    currency_id = db.Column(db.Integer, db.ForeignKey('currency.id'))
    currency = db.relationship('Currency')
    exchange_rate = db.Column(db.Numeric(14, 6))

    status = db.Column(db.String(50), default='Unpaid')
    # Unpaid / Partial / Paid

    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')


class AccountsReceivable(db.Model):
    __tablename__ = 'accounts_receivable'

    id = db.Column(db.Integer, primary_key=True)
    bulk_buyer_id = db.Column(db.Integer, db.ForeignKey('bulk_buyer.id'), nullable=False)
    bulk_buyer = db.relationship('BulkBuyer', backref='receivables')

    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'))
    sale = db.relationship('Sale', backref='receivable')

    amount_due = db.Column(db.Numeric(14, 2), nullable=False)
    amount_paid = db.Column(db.Numeric(14, 2), default=0)

    status = db.Column(db.String(50), default='Unpaid')
    # Unpaid / Partial / Paid

    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')


class Payment(db.Model):
    __tablename__ = 'payment'

    id = db.Column(db.Integer, primary_key=True)
    payment_type = db.Column(db.String(20), nullable=False)
    # outgoing (to supplier) / incoming (from bulk buyer)

    payable_id = db.Column(db.Integer, db.ForeignKey('accounts_payable.id'))
    payable = db.relationship('AccountsPayable', backref='payments')

    receivable_id = db.Column(db.Integer, db.ForeignKey('accounts_receivable.id'))
    receivable = db.relationship('AccountsReceivable', backref='payments')

    amount = db.Column(db.Numeric(14, 2), nullable=False)
    currency_id = db.Column(db.Integer, db.ForeignKey('currency.id'))
    currency = db.relationship('Currency')
    exchange_rate = db.Column(db.Numeric(14, 6))

    payment_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')


class TaxEntry(db.Model):
    __tablename__ = 'tax_entry'

    id = db.Column(db.Integer, primary_key=True)
    tax_type = db.Column(db.String(20), nullable=False)
    # collected (from customers) / paid (on imports)

    amount = db.Column(db.Numeric(14, 2), nullable=False)
    tax_rate = db.Column(db.Numeric(5, 4), nullable=False)

    reference_id = db.Column(db.Integer)
    reference_type = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')