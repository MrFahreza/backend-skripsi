# backend/app/login/__init__.py

from flask import Blueprint

# Membuat Blueprint bernama 'login'
login_bp = Blueprint('login', __name__)

# Import rute agar ter-registrasi dengan blueprint
from . import routes