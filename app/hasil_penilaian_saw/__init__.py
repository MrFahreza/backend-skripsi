# backend/app/hasil_penilaian_saw/__init__.py

from flask import Blueprint

# Membuat Blueprint dengan prefix URL /hasil-saw
saw_bp = Blueprint('hasil_saw', __name__, url_prefix='/hasil-saw')

from . import routes