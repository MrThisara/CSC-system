from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_login import login_required, current_user
from app.extensions import bcrypt, db
from app.models.user import User
from app.models.audit import AuditLog
from . import auth_bp
from .forms import LoginForm


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)

            log = AuditLog(
                tier='standard',
                action='user_login',
                entity_type='user',
                entity_id=user.id,
                description=f'{user.full_name} logged in.',
                performed_by_id=user.id,
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()

            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Incorrect email or password.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    log = AuditLog(
        tier='standard',
        action='user_logout',
        entity_type='user',
        entity_id=current_user.id,
        description=f'{current_user.full_name} logged out.',
        performed_by_id=current_user.id,
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()

    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    from .forms import ChangePasswordForm
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not bcrypt.check_password_hash(current_user.password_hash,
                                          form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('auth.change_password'))

        current_user.password_hash = bcrypt.generate_password_hash(
            form.new_password.data).decode('utf-8')

        log = AuditLog(
            tier='standard',
            action='password_changed',
            entity_type='user',
            entity_id=current_user.id,
            description=f'{current_user.full_name} changed their password.',
            performed_by_id=current_user.id,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/change_password.html', form=form)