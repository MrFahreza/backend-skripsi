# backend/app/pengaturan_jadwal/__init__.py
from flask import Blueprint

jadwal_bp = Blueprint('jadwal', __name__, url_prefix='/jadwal')

from . import routes