from app.extensions import db
from datetime import datetime


class Supplier(db.Model):
    __tablename__ = 'supplier'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact_name = db.Column(db.String(200))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    country = db.Column(db.String(100))
    lead_time_days = db.Column(db.Integer)
    # How many days this supplier typically takes to deliver

    currency_id = db.Column(db.Integer, db.ForeignKey('currency.id'))
    currency = db.relationship('Currency')
    # The currency this supplier invoices in (e.g. USD, CNY)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')


class Product(db.Model):
    __tablename__ = 'product'

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    unit_id = db.Column(db.Integer, db.ForeignKey('unit_of_measurement.id'))
    unit = db.relationship('UnitOfMeasurement')

    # Stock fields — all in one place as per your spec
    warehouse_stock = db.Column(db.Numeric(12, 4), default=0)
    warehouse_reorder_threshold = db.Column(db.Numeric(12, 4), default=0)
    shelf_stock = db.Column(db.Numeric(12, 4), default=0)
    shelf_reorder_threshold = db.Column(db.Numeric(12, 4), default=0)
    bulk_limit = db.Column(db.Numeric(12, 4), default=0)
    # Maximum quantity a walk-in customer can buy in one transaction

    # Costing — AVCO method
    avco_cost = db.Column(db.Numeric(14, 4), default=0)
    # Current average cost per unit in JPY (recalculated on every goods receipt)

    # Selling price in JPY (before tax)
    selling_price = db.Column(db.Numeric(14, 4), default=0)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')


class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_order'

    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), unique=True, nullable=False)
    # e.g. 'PO-2024-0001'

    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    supplier = db.relationship('Supplier', backref='purchase_orders')

    status = db.Column(db.String(50), nullable=False, default='Draft')
    # Draft → Submitted → Approved / Rejected → Sent to Supplier → Goods Received

    currency_id = db.Column(db.Integer, db.ForeignKey('currency.id'))
    currency = db.relationship('Currency')
    exchange_rate = db.Column(db.Numeric(14, 6))
    # Exchange rate to JPY at time of this PO (e.g. 1 USD = 149.50 JPY)

    notes = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    submitted_at = db.Column(db.DateTime)
    approved_at = db.Column(db.DateTime)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])

    sent_at = db.Column(db.DateTime)
    expected_delivery = db.Column(db.Date)

    # Line items
    items = db.relationship('PurchaseOrderItem', backref='purchase_order',
                            lazy='dynamic', cascade='all, delete-orphan')


class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_item'

    id = db.Column(db.Integer, primary_key=True)
    po_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=False)

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')

    quantity = db.Column(db.Numeric(12, 4), nullable=False)
    unit_price = db.Column(db.Numeric(14, 4), nullable=False)
    # Price in the supplier's currency

    quantity_received = db.Column(db.Numeric(12, 4), default=0)
    # Filled in when goods are received — may differ from ordered quantity


class Shipment(db.Model):
    __tablename__ = 'shipment'

    id = db.Column(db.Integer, primary_key=True)
    po_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=False)
    purchase_order = db.relationship('PurchaseOrder', backref='shipments')

    tracking_number = db.Column(db.String(200))
    carrier = db.Column(db.String(200))

    status = db.Column(db.String(50), default='Pending')
    # Pending → In Transit → Arrived → Cleared

    shipped_date = db.Column(db.Date)
    estimated_arrival = db.Column(db.Date)
    actual_arrival = db.Column(db.Date)

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LandedCost(db.Model):
    __tablename__ = 'landed_cost'

    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey('shipment.id'), nullable=False)
    shipment = db.relationship('Shipment', backref='landed_costs')

    freight = db.Column(db.Numeric(14, 2), default=0)
    import_duty = db.Column(db.Numeric(14, 2), default=0)
    insurance = db.Column(db.Numeric(14, 2), default=0)
    other = db.Column(db.Numeric(14, 2), default=0)
    # Any other miscellaneous costs

    total = db.Column(db.Numeric(14, 2), default=0)
    # freight + import_duty + insurance + other
    # This gets allocated across products in the shipment

    currency_id = db.Column(db.Integer, db.ForeignKey('currency.id'))
    currency = db.relationship('Currency')
    exchange_rate = db.Column(db.Numeric(14, 6))

    recorded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recorded_by = db.relationship('User')
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)


class LandedCostAllocation(db.Model):
    __tablename__ = 'landed_cost_allocation'

    id = db.Column(db.Integer, primary_key=True)
    landed_cost_id = db.Column(db.Integer, db.ForeignKey('landed_cost.id'), nullable=False)
    landed_cost = db.relationship('LandedCost', backref='allocations')

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')

    allocated_amount = db.Column(db.Numeric(14, 4), nullable=False)
    # The share of total landed cost assigned to this product in JPY


class SupplierReturn(db.Model):
    __tablename__ = 'supplier_return'

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    supplier = db.relationship('Supplier', backref='returns')

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