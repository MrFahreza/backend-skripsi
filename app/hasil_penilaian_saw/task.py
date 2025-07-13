from flask import current_app
from .routes import _run_saw_calculation_logic
from ..utils.email_utils import send_admin_notification_email

def scheduled_saw_task(app, period_name):
    print(f"--- Menjalankan Tugas Terjadwal SAW untuk Periode: {period_name} ---")
    
    result = _run_saw_calculation_logic(app)
    
    if result["success"]:
        with app.app_context():
            admin = current_app.db.admins.find_one({"username": "admin"})
            if admin and admin.get("email"):
                mail_config = {
                    "MAIL_SERVER": current_app.config['MAIL_SERVER'],
                    "MAIL_PORT": current_app.config['MAIL_PORT'],
                    "MAIL_USERNAME": current_app.config['MAIL_USERNAME'],
                    "MAIL_PASSWORD": current_app.config['MAIL_PASSWORD']
                }
                send_admin_notification_email(admin['email'], period_name, mail_config)
    print(f"--- Tugas Terjadwal SAW Selesai ---")