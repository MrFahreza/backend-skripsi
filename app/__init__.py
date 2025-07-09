import os
from flask import Flask
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler 

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

    # --- Registrasi Blueprint ---
    from .login import login_bp
    app.register_blueprint(login_bp)

    from .data_mahasiswa import mahasiswa_bp
    app.register_blueprint(mahasiswa_bp)
    
    from .penilaian_mahasiswa import penilaian_bp
    app.register_blueprint(penilaian_bp)

    from .hasil_penilaian_saw import saw_bp
    app.register_blueprint(saw_bp)

    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        from .hasil_penilaian_saw.task import scheduled_saw_task
        
        scheduler = BackgroundScheduler(daemon=True, timezone='Asia/Jakarta')
        
        # Jadwal #1: Setelah UTS
        scheduler.add_job(
            func=scheduled_saw_task,
            args=[app, "UTS"],
            trigger='cron',
            month='7', day='10', hour='0', minute='12'
        )
        
        # Jadwal #2: Setelah UAS
        scheduler.add_job(
            func=scheduled_saw_task,
            args=[app, "UAS"],
            trigger='cron',
            month='12', day='1', hour='2', minute='10'
        )
        
        scheduler.start()
        print("Scheduler untuk perhitungan otomatis telah dimulai.")

    return app