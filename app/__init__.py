# backend/app/__init__.py

import os
from flask import Flask
from pymongo import MongoClient
from dotenv import load_dotenv

def create_app():
    app = Flask(__name__)
    load_dotenv()

    # --- Muat Konfigurasi ---
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    # Muat konfigurasi email dari .env
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

    # --- Koneksi Database ---
    MONGO_URI = os.getenv('MONGO_URI')
    client = MongoClient(MONGO_URI)
    app.db = client['admin_db']

    # --- Registrasi Blueprint ---
    from .login import login_bp
    app.register_blueprint(login_bp)

    # DAFTARKAN BLUEPRINT BARU DI SINI
    from .data_mahasiswa import mahasiswa_bp
    app.register_blueprint(mahasiswa_bp)

    from .penilaian_mahasiswa import penilaian_bp
    app.register_blueprint(penilaian_bp)

    return app