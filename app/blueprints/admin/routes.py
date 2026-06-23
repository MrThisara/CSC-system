from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db, bcrypt
from app.models.admin import CompanySettings, Currency, UnitOfMeasurement
from app.models.user import User, Role
from app.models.audit import AuditLog
from . import admin_bp
from .forms import CompanySettingsForm, CurrencyForm, UnitForm, UserForm


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


# --- Company Settings ---

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def company_settings():
    if not require_permission('manage_company_settings'):
        return redirect(url_for('main.dashboard'))

    settings = CompanySettings.query.first()
    form = CompanySettingsForm(obj=settings)

    if form.validate_on_submit():
        if settings:
            old = f'tax_rate={settings.tax_rate}, name={settings.company_name}'
            settings.company_name = form.company_name.data
            settings.address = form.address.data
            settings.phone = form.phone.data
            settings.email = form.email.data
            settings.tax_rate = form.tax_rate.data
            settings.base_currency = form.base_currency.data
            settings.updated_by_id = current_user.id
            new = f'tax_rate={settings.tax_rate}, name={settings.company_name}'
            log('critical', 'tax_rate_changed', 'company_settings', settings.id,
                'Company settings updated.', old, new)
        else:
            settings = CompanySettings(
                company_name=form.company_name.data,
                address=form.address.data,
                phone=form.phone.data,
                email=form.email.data,
                tax_rate=form.tax_rate.data,
                base_currency=form.base_currency.data,
                updated_by_id=current_user.id
            )
            db.session.add(settings)
            log('standard', 'company_settings_created', 'company_settings', None,
                'Company settings created.')

        db.session.commit()
        flash('Company settings saved.', 'success')
        return redirect(url_for('admin.company_settings'))

    return render_template('admin/settings.html', form=form)


# --- Currencies ---

@admin_bp.route('/currencies')
@login_required
def currencies():
    if not require_permission('manage_currencies'):
        return redirect(url_for('main.dashboard'))
    all_currencies = Currency.query.order_by(Currency.code).all()
    form = CurrencyForm()
    return render_template('admin/currencies.html', currencies=all_currencies, form=form)


@admin_bp.route('/currencies/add', methods=['POST'])
@login_required
def add_currency():
    if not require_permission('manage_currencies'):
        return redirect(url_for('main.dashboard'))
    form = CurrencyForm()
    if form.validate_on_submit():
        existing = Currency.query.filter_by(code=form.code.data.upper()).first()
        if existing:
            flash(f'Currency {form.code.data.upper()} already exists.', 'danger')
            return redirect(url_for('admin.currencies'))
        currency = Currency(
            code=form.code.data.upper(),
            name=form.name.data,
            symbol=form.symbol.data,
            is_active=form.is_active.data
        )
        db.session.add(currency)
        db.session.commit()
        flash(f'Currency {currency.code} added.', 'success')
    return redirect(url_for('admin.currencies'))


@admin_bp.route('/currencies/<int:id>/toggle')
@login_required
def toggle_currency(id):
    if not require_permission('manage_currencies'):
        return redirect(url_for('main.dashboard'))
    currency = Currency.query.get_or_404(id)
    currency.is_active = not currency.is_active
    db.session.commit()
    flash(f'Currency {currency.code} updated.', 'success')
    return redirect(url_for('admin.currencies'))


# --- Units of Measurement ---

@admin_bp.route('/units')
@login_required
def units():
    if not require_permission('manage_units'):
        return redirect(url_for('main.dashboard'))
    all_units = UnitOfMeasurement.query.order_by(UnitOfMeasurement.name).all()
    form = UnitForm()
    return render_template('admin/units.html', units=all_units, form=form)


@admin_bp.route('/units/add', methods=['POST'])
@login_required
def add_unit():
    if not require_permission('manage_units'):
        return redirect(url_for('main.dashboard'))
    form = UnitForm()
    if form.validate_on_submit():
        existing = UnitOfMeasurement.query.filter_by(name=form.name.data).first()
        if existing:
            flash(f'Unit {form.name.data} already exists.', 'danger')
            return redirect(url_for('admin.units'))
        unit = UnitOfMeasurement(
            name=form.name.data,
            abbreviation=form.abbreviation.data,
            is_active=form.is_active.data
        )
        db.session.add(unit)
        db.session.commit()
        flash(f'Unit {unit.name} added.', 'success')
    return redirect(url_for('admin.units'))


@admin_bp.route('/units/<int:id>/toggle')
@login_required
def toggle_unit(id):
    if not require_permission('manage_units'):
        return redirect(url_for('main.dashboard'))
    unit = UnitOfMeasurement.query.get_or_404(id)
    unit.is_active = not unit.is_active
    db.session.commit()
    flash(f'Unit {unit.name} updated.', 'success')
    return redirect(url_for('admin.units'))


# --- Users ---

@admin_bp.route('/users')
@login_required
def users():
    if not require_permission('manage_users'):
        return redirect(url_for('main.dashboard'))
    all_users = User.query.order_by(User.full_name).all()
    all_roles = Role.query.order_by(Role.name).all()
    form = UserForm()
    return render_template('admin/users.html', users=all_users, roles=all_roles, form=form)


@admin_bp.route('/users/add', methods=['POST'])
@login_required
def add_user():
    if not require_permission('manage_users'):
        return redirect(url_for('main.dashboard'))
    form = UserForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(email=form.email.data).first()
        if existing:
            flash(f'A user with email {form.email.data} already exists.', 'danger')
            return redirect(url_for('admin.users'))
        role_id = request.form.get('role_id')
        hashed = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            full_name=form.full_name.data,
            email=form.email.data,
            password_hash=hashed,
            role_id=role_id
        )
        db.session.add(user)
        db.session.flush()
        log('standard', 'user_created', 'user', user.id,
            f'User {user.full_name} created.')
        db.session.commit()
        flash(f'User {user.full_name} created.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:id>/toggle')
@login_required
def toggle_user(id):
    if not require_permission('manage_users'):
        return redirect(url_for('main.dashboard'))
    user = User.query.get_or_404(id)
    user.is_active = not user.is_active
    db.session.commit()
    flash(f'User {user.full_name} updated.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:id>/role', methods=['POST'])
@login_required
def assign_role(id):
    if not require_permission('assign_roles'):
        return redirect(url_for('main.dashboard'))
    user = User.query.get_or_404(id)
    new_role_id = request.form.get('role_id')
    old_role = user.role.name
    user.role_id = new_role_id
    new_role = Role.query.get(new_role_id)
    log('standard', 'role_assigned', 'user', user.id,
        f'Role changed from {old_role} to {new_role.name}.')
    db.session.commit()
    flash(f'Role updated for {user.full_name}.', 'success')
    return redirect(url_for('admin.users'))

# --- Audit Log ---2

@admin_bp.route('/audit-log')
@login_required
def audit_log():
    if not require_permission('manage_users'):
        return redirect(url_for('main.dashboard'))

    tier = request.args.get('tier', '')
    action = request.args.get('action', '')
    user_id = request.args.get('user_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = AuditLog.query

    if tier:
        query = query.filter(AuditLog.tier == tier)
    if action:
        query = query.filter(AuditLog.action.ilike(f'%{action}%'))
    if user_id:
        query = query.filter(AuditLog.performed_by_id == int(user_id))
    if date_from:
        query = query.filter(AuditLog.performed_at >= date_from)
    if date_to:
        query = query.filter(AuditLog.performed_at <= date_to + ' 23:59:59')

    entries = query.order_by(AuditLog.performed_at.desc()).limit(500).all()
    all_users = User.query.order_by(User.full_name).all()

    return render_template('admin/audit_log.html',
                           entries=entries,
                           all_users=all_users,
                           filters={
                               'tier': tier,
                               'action': action,
                               'user_id': user_id,
                               'date_from': date_from,
                               'date_to': date_to
                           })