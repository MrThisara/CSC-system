from flask import Blueprint

reporting_bp = Blueprint('reporting', __name__, url_prefix='/reports')

from . import routes