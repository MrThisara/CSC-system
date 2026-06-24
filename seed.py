from app import create_app
from app.extensions import db, bcrypt
from app.models.user import User, Role, Permission
import os

app = create_app()

PERMISSIONS = [
    # Admin
    ('manage_company_settings', 'Edit company settings and tax rate'),
    ('manage_currencies', 'Add and edit currencies'),
    ('manage_units', 'Add and edit units of measurement'),

    # Users
    ('manage_users', 'Create and deactivate users'),
    ('assign_roles', 'Assign roles to users'),
    ('view_users', 'View user list'),

    # Procurement
    ('manage_suppliers', 'Create and edit suppliers'),
    ('manage_products', 'Create and edit products'),
    ('create_po', 'Create and submit purchase orders'),
    ('approve_po', 'Approve or reject purchase orders'),
    ('send_po', 'Mark PO as sent to supplier'),
    ('receive_goods', 'Record goods received'),
    ('manage_landed_costs', 'Record landed costs and allocations'),
    ('manage_shipments', 'Create and update shipments'),
    ('manage_supplier_returns', 'Initiate and complete supplier returns'),

    # Warehouse
    ('view_inventory', 'View warehouse stock levels'),
    ('adjust_stock', 'Manually adjust stock'),
    ('write_off_stock', 'Write off damaged or lost stock'),
    ('approve_transfers', 'Approve or reject stock transfer requests'),
    ('manage_warehouse_locations', 'Create and edit warehouse locations'),
    ('set_warehouse_threshold', 'Set warehouse reorder thresholds'),

    # Sales
    ('manage_customers', 'Create and edit bulk buyer accounts'),
    ('create_sale', 'Process walk-in and bulk sales'),
    ('cancel_sale', 'Cancel a sale'),
    ('manage_bulk_orders', 'Update bulk order delivery status'),
    ('create_transfer_request', 'Request stock transfer from warehouse'),
    ('set_shelf_threshold', 'Set shelf reorder thresholds'),
    ('set_bulk_limit', 'Set bulk limit on products'),
    ('manage_customer_returns', 'Process customer returns'),
    ('view_invoices', 'View invoices'),

    # Accounting
    ('view_ledger', 'View the ledger'),
    ('edit_ledger', 'Manually edit ledger entries'),
    ('manage_payables', 'Record and manage accounts payable'),
    ('manage_receivables', 'Record and manage accounts receivable'),
    ('record_payments', 'Record payments to suppliers or from buyers'),
    ('manage_tax_entries', 'Record and view tax entries'),

    # Reporting
    ('view_reports', 'View all reports and dashboard'),
    ('export_reports', 'Export reports'),
]

ROLES = {
    'CEO': [p[0] for p in PERMISSIONS],

    'Procurement Officer': [
        'manage_suppliers', 'manage_products', 'create_po', 'send_po',
        'receive_goods', 'manage_landed_costs', 'manage_shipments',
        'manage_supplier_returns', 'view_inventory', 'view_reports',
        'view_invoices',
    ],

    'Warehouse Manager': [
        'view_inventory', 'adjust_stock', 'write_off_stock', 'approve_transfers',
        'manage_warehouse_locations', 'set_warehouse_threshold', 'receive_goods',
        'view_reports',
    ],

    'Warehouse Worker': [
        'view_inventory', 'receive_goods',
    ],

    'Sales Staff': [
        'manage_customers', 'create_sale', 'cancel_sale', 'manage_bulk_orders',
        'create_transfer_request', 'set_shelf_threshold', 'set_bulk_limit',
        'manage_customer_returns', 'view_invoices', 'view_reports',
    ],

    'Accountant': [
        'view_ledger', 'edit_ledger', 'manage_payables', 'manage_receivables',
        'record_payments', 'manage_tax_entries', 'view_reports', 'export_reports',
        'view_invoices',
    ],
}

DEFAULT_CEO = {
    'full_name': os.environ.get ('SEED_ADMIN_NAME', 'System Admin'),
    'email': os.environ.get ('SEED_ADMIN_EMAIL' 'admin@erp.com'),
    'password': os.environ.get ('SEED_ADMIN_PASSWORD' 'admin1234'),
}

def seed():
    with app.app_context():
        print("Seeding permissions...")
        permission_map = {}
        for name, description in PERMISSIONS:
            existing = Permission.query.filter_by(name=name).first()
            if not existing:
                p = Permission(name=name, description=description)
                db.session.add(p)
                db.session.flush()
                permission_map[name] = p
            else:
                permission_map[name] = existing
        
        print("Seeding roles...")
        role_map = {}
        for role_name, perm_names in ROLES.items():
            existing = Role.query.filter_by(name=role_name).first()
            if not existing:
                r = Role(name=role_name)
                db.session.add(r)
                db.session.flush()
                role_map[role_name] = r
            else:
                role_map[role_name] = existing

            for perm_name in perm_names:
                perm = permission_map.get(perm_name)
                if perm and perm not in role_map[role_name].permissions:
                    role_map[role_name].permissions.append(perm)

        print("Seeding default CEO user...")
        existing_user = User.query.filter_by(email=DEFAULT_CEO['email']).first()
        if not existing_user:
            ceo_role = role_map.get('CEO')
            hashed = bcrypt.generate_password_hash(DEFAULT_CEO['password']).decode('utf-8')
            user = User(
                full_name=DEFAULT_CEO['full_name'],
                email=DEFAULT_CEO['email'],
                password_hash=hashed,
                role=ceo_role,
            )
            db.session.add(user)

        db.session.commit()
        print("Done. Default login -> email: admin@erp.com / password: admin1234")

if __name__ == '__main__':
    seed()