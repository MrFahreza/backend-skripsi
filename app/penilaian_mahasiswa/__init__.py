# backend/app/penilaian_mahasiswa/__init__.py

from flask import Blueprint

# Membuat Blueprint dengan prefix URL /penilaian
penilaian_bp = Blueprint('penilaian', __name__, url_prefix='/penilaian')

# Import rute agar ter-registrasi dengan blueprint
from . import routes