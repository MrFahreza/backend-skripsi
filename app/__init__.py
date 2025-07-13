import os
from flask import Flask
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler 
from apscheduler.schedulers.background import BackgroundScheduler
from flask_apscheduler import APScheduler

scheduler = APScheduler()

def create_app():
    app = Flask(__name__)
    load_dotenv()
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

    # --- Scheduler ---
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler.init_app(app)
        scheduler.start()
        print("Scheduler telah dimulai oleh Flask-APScheduler.")
    app.scheduler = scheduler

    # --- Registrasi Blueprint ---
    from .login import login_bp
    app.register_blueprint(login_bp)

    from .data_mahasiswa import mahasiswa_bp
    app.register_blueprint(mahasiswa_bp)
    
    from .penilaian_mahasiswa import penilaian_bp
    app.register_blueprint(penilaian_bp)

    from .hasil_penilaian_saw import saw_bp
    app.register_blueprint(saw_bp)

    from .pengaturan_jadwal import jadwal_bp
    app.register_blueprint(jadwal_bp)

    return app