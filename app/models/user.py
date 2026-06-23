from app.extensions import db
from flask_login import UserMixin
from datetime import datetime

# This is a "junction table" — it links roles to permissions.
# It's not a full model, just a simple connection table, so we define it
# differently (no class, just a plain table).
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'), primary_key=True)
)


class Permission(db.Model):
    __tablename__ = 'permission'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    # e.g. 'approve_po', 'manage_inventory', 'view_reports'
    description = db.Column(db.String(255))


class Role(db.Model):
    __tablename__ = 'role'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    # e.g. 'CEO', 'Procurement Officer', 'Warehouse Manager', etc.
    description = db.Column(db.String(255))

    # A role can have many permissions, a permission can belong to many roles
    permissions = db.relationship('Permission', secondary=role_permissions,
                                  backref='roles', lazy='dynamic')


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # Each user has one role (e.g. Warehouse Manager)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    role = db.relationship('Role', backref='users')

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def has_permission(self, permission_name):
        """Check if this user's role includes a specific permission."""
        return self.role.permissions.filter_by(name=permission_name).first() is not None

    def __repr__(self):
        return f'<User {self.email}>'