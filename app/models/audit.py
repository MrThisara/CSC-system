from app.extensions import db
from datetime import datetime


class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    tier = db.Column(db.String(20), nullable=False)
    # critical / standard

    action = db.Column(db.String(100), nullable=False)
    # e.g. 'po_approved', 'goods_received', 'tax_rate_changed'

    entity_type = db.Column(db.String(50))
    # e.g. 'purchase_order', 'product', 'user'

    entity_id = db.Column(db.Integer)
    # the id of the record that was affected

    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    # only populated for critical tier entries

    description = db.Column(db.Text)
    # human readable summary of what happened

    performed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    performed_by = db.relationship('User')
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))