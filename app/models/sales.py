from app.extensions import db
from datetime import datetime


class BulkBuyer(db.Model):
    __tablename__ = 'bulk_buyer'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(200), unique=True)
    delivery_address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')


class Sale(db.Model):
    __tablename__ = 'sale'

    id = db.Column(db.Integer, primary_key=True)
    sale_number = db.Column(db.String(50), unique=True, nullable=False)

    sale_type = db.Column(db.String(20), nullable=False)
    # walk_in / bulk_order

    bulk_buyer_id = db.Column(db.Integer, db.ForeignKey('bulk_buyer.id'))
    bulk_buyer = db.relationship('BulkBuyer', backref='sales')

    status = db.Column(db.String(50), nullable=False, default='Completed')
    # Completed / Cancelled

    tax_rate = db.Column(db.Numeric(5, 4), nullable=False)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')

    items = db.relationship('SaleItem', backref='sale',
                            lazy='dynamic', cascade='all, delete-orphan')


class SaleItem(db.Model):
    __tablename__ = 'sale_item'

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')

    quantity = db.Column(db.Numeric(12, 4), nullable=False)
    unit_price = db.Column(db.Numeric(14, 4), nullable=False)
    avco_cost_at_sale = db.Column(db.Numeric(14, 4), nullable=False)
    line_total = db.Column(db.Numeric(14, 2), nullable=False)


class BulkOrder(db.Model):
    __tablename__ = 'bulk_order'

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False, unique=True)
    sale = db.relationship('Sale', backref='bulk_order')

    dispatched_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    dispatched_by = db.relationship('User')

    estimated_days = db.Column(db.Integer)
    delivery_status = db.Column(db.String(50), default='Pending')
    # Pending → Dispatched → Delivered

    dispatched_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)


class Invoice(db.Model):
    __tablename__ = 'invoice'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False, unique=True)
    sale = db.relationship('Sale', backref='invoice')

    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    issued_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    issued_by = db.relationship('User')


class CustomerReturn(db.Model):
    __tablename__ = 'customer_return'

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    sale = db.relationship('Sale', backref='returns')

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')

    quantity = db.Column(db.Numeric(12, 4), nullable=False)
    reason = db.Column(db.Text)

    status = db.Column(db.String(50), default='Pending')
    # Pending → Completed

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    completed_at = db.Column(db.DateTime)
    completed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    completed_by = db.relationship('User', foreign_keys=[completed_by_id])