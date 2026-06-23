from flask import Flask, app

from app import models
from .extensions import db, migrate, login_manager, bcrypt, csrf
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)

    from app import models
    
    # Register blueprints (modules)
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.procurement import procurement_bp
    from app.blueprints.warehouse import warehouse_bp
    from app.blueprints.sales import sales_bp
    from app.blueprints.accounting import accounting_bp
    from app.blueprints.reporting import reporting_bp
    app.register_blueprint(reporting_bp)
    app.register_blueprint(accounting_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(warehouse_bp)
    app.register_blueprint(procurement_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    return app