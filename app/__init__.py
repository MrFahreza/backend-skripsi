import os
from flask import Flask
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_cors import CORS
from flask_apscheduler import APScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore

scheduler = APScheduler()

def create_app(init_scheduler=True):
    app = Flask(__name__)
    CORS(app) 
    load_dotenv()
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT')) if os.getenv('MAIL_PORT') else 587
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    
    MONGO_URI = os.getenv('MONGO_URI')
    client = MongoClient(MONGO_URI)
    app.db = client['admin_db']

    app.config["SCHEDULER_JOBSTORES"] = {
        "default": MongoDBJobStore(database="admin_db", collection="jadwal_otomatis", client=client)
    }
    app.config["SCHEDULER_API_ENABLED"] = True

    if init_scheduler:
        scheduler.init_app(app)
        if not scheduler.running:
            scheduler.start()
            print("Scheduler telah diinisialisasi dan dimulai.")
    
    app.scheduler = scheduler

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