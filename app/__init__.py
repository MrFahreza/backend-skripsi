# backend/app/__init__.py

import os
from flask import Flask
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_cors import CORS # 1. IMPORT CORS DI SINI

def create_app():
    app = Flask(__name__)
    load_dotenv()

    # 2. TERAPKAN CORS KE APLIKASI ANDA
    # Ini akan mengizinkan semua domain untuk mengakses API Anda
    CORS(app) 

    # --- Muat Konfigurasi ---
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
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

    from .data_mahasiswa import mahasiswa_bp
    app.register_blueprint(mahasiswa_bp)
    
    from .penilaian_mahasiswa import penilaian_bp
    app.register_blueprint(penilaian_bp)

    from .hasil_penilaian_saw import saw_bp
    app.register_blueprint(saw_bp)

    return app