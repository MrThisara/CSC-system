from app.extensions import db
from datetime import datetime


class CompanySettings(db.Model):
    __tablename__ = 'company_settings'

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(200))
    tax_rate = db.Column(db.Numeric(5, 4), nullable=False, default=0.10)
    # e.g. 0.1000 = 10%. Stored as a decimal, never hardcoded elsewhere.

    base_currency = db.Column(db.String(10), nullable=False, default='JPY')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_by = db.relationship('User')


class Currency(db.Model):
    __tablename__ = 'currency'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    # e.g. 'USD', 'EUR', 'CNY'
    name = db.Column(db.String(100), nullable=False)
    # e.g. 'US Dollar'
    symbol = db.Column(db.String(10))
    # e.g. '$', '€', '¥'
    is_active = db.Column(db.Boolean, default=True)


class UnitOfMeasurement(db.Model):
    __tablename__ = 'unit_of_measurement'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    # e.g. 'piece', 'kilogram', 'box', 'carton'
    abbreviation = db.Column(db.String(20))
    # e.g. 'pcs', 'kg', 'box'
    is_active = db.Column(db.Boolean, default=True)