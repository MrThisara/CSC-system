from app.extensions import db
from datetime import datetime


class WarehouseLocation(db.Model):
    __tablename__ = 'warehouse_location'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class StockTransferRequest(db.Model):
    __tablename__ = 'stock_transfer_request'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')

    quantity = db.Column(db.Numeric(12, 4), nullable=False)

    status = db.Column(db.String(50), nullable=False, default='Pending')
    # Pending → Approved / Rejected

    rejection_reason = db.Column(db.Text)

    requested_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requested_by = db.relationship('User', foreign_keys=[requested_by_id])

    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])

    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)


class StockMovement(db.Model):
    __tablename__ = 'stock_movement'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')

    movement_type = db.Column(db.String(50), nullable=False)
    # goods_received / transfer_out / transfer_in / write_off / sale / return

    quantity = db.Column(db.Numeric(12, 4), nullable=False)
    reference_id = db.Column(db.Integer)
    reference_type = db.Column(db.String(50))
    # e.g. reference_type='transfer_request', reference_id=7

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User')


class StockWriteOff(db.Model):
    __tablename__ = 'stock_write_off'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')

    quantity = db.Column(db.Numeric(12, 4), nullable=False)
    reason = db.Column(db.Text)

    written_off_at = db.Column(db.DateTime, default=datetime.utcnow)
    written_off_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    written_off_by = db.relationship('User')