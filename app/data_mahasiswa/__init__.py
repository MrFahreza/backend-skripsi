from flask import Blueprint

# Membuat Blueprint dengan prefix URL /mahasiswa
mahasiswa_bp = Blueprint('mahasiswa', __name__, url_prefix='/mahasiswa')

# Import rute agar ter-registrasi dengan blueprint
from . import routes