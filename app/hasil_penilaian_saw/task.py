# backend/app/hasil_penilaian_saw/tasks.py
    
from .. import create_app
from datetime import datetime, timezone
from pymongo import UpdateOne

# Import dari file utils yang sudah kita buat
from ..hasil_penilaian_saw.routes import _get_rating, BOBOT_SAW
# Import fungsi email dari utils
from ..utils.email_utils import send_admin_notification_email, send_saw_warning_email, send_saw_congrats_email

def scheduled_saw_task(period_name, job_id):
    """
    Tugas mandiri yang berisi semua logika dan dijalankan oleh scheduler.
    """
    print(f"--- Menjalankan Tugas Terjadwal (ID: {job_id}) untuk Periode: {period_name} ---")

    app = create_app(init_scheduler=False)
    
    # Flask-APScheduler akan menyediakan konteks aplikasi secara otomatis
    penilaian_collection = app.db.penilaian_mahasiswa
    mahasiswa_collection = app.db.mahasiswa
    
    all_penilaian = list(penilaian_collection.find({}))
    if not all_penilaian:
        print(f"Tugas {job_id} dibatalkan: Tidak ada data penilaian untuk dihitung.")
        app.db.jadwal_saw.update_one({"job_id": job_id}, {"$set": {"status": True}})
        return

    student_emails = {m['npm']: m['email'] for m in mahasiswa_collection.find({}, {'npm': 1, 'email': 1})}
    
    # Tahap 1: Membuat Matriks Keputusan (X)
    matriks_x = []
    for p in all_penilaian:
        c1 = p.get('keaktifan_organisasi', 0)
        c2 = p.get('ipk', 0)
        c3 = p.get('persentase_kehadiran', 0)
        r1, r2, r3 = _get_rating(c1, c2, c3)
        matriks_x.append({"npm": p['npm'], "nama": p['nama'], "c1_rated": r1, "c2_rated": r2, "c3_rated": r3})

    # Tahap 2: Menentukan Nilai Max
    max_c1_relatif = max((item['c1_rated'] for item in matriks_x), default=1)
    max_c2_relatif = max((item['c2_rated'] for item in matriks_x), default=1)
    max_c3_relatif = max((item['c3_rated'] for item in matriks_x), default=1)
    MAX_STANDAR = 5.0

    # Tahap 3: Perangkingan, Penentuan Status, dan Notifikasi Mahasiswa
    hasil_akhir = []
    mail_config = {
        "MAIL_SERVER": app.config['MAIL_SERVER'],
        "MAIL_PORT": app.config['MAIL_PORT'],
        "MAIL_USERNAME": app.config['MAIL_USERNAME'],
        "MAIL_PASSWORD": app.config['MAIL_PASSWORD']
    }

    for i, item_x in enumerate(matriks_x):
        original_assessment = all_penilaian[i]
        
        r1_relatif = item_x['c1_rated'] / max_c1_relatif
        r2_relatif = item_x['c2_rated'] / max_c2_relatif
        r3_relatif = item_x['c3_rated'] / max_c3_relatif
        # --- PERBAIKAN KUNCI: Gunakan 'c1', 'c2', 'c3' ---
        skor_akhir_saw = ((r1_relatif * BOBOT_SAW['c1']) + (r2_relatif * BOBOT_SAW['c2']) + (r3_relatif * BOBOT_SAW['c3']))

        r1_standar = item_x['c1_rated'] / MAX_STANDAR
        r2_standar = item_x['c2_rated'] / MAX_STANDAR
        r3_standar = item_x['c3_rated'] / MAX_STANDAR
        # --- PERBAIKAN KUNCI: Gunakan 'c1', 'c2', 'c3' ---
        skor_akhir_standar = ((r1_standar * BOBOT_SAW['c1']) + (r2_standar * BOBOT_SAW['c2']) + (r3_standar * BOBOT_SAW['c3']))
        
        student_email = student_emails.get(item_x['npm'])
        status = "Standar Terpenuhi"
        
        if student_email:
            if skor_akhir_standar < 0.7:
                status = "Perlu Peringatan"
                kriteria_lemah = []
                if item_x['c1_rated'] <= 2: kriteria_lemah.append("Keaktifan Organisasi")
                if item_x['c2_rated'] <= 3: kriteria_lemah.append("IPK")
                if item_x['c3_rated'] <= 2: kriteria_lemah.append("Persentase Kehadiran")
                if kriteria_lemah:
                    send_saw_warning_email(student_email, item_x['nama'], kriteria_lemah, original_assessment, mail_config, period_name)
            else:
                send_saw_congrats_email(student_email, item_x['nama'], original_assessment, mail_config, period_name)

        hasil_akhir.append({
            "npm": item_x['npm'], "nama": item_x['nama'],
            "skor_akhir_saw": round(skor_akhir_saw, 4),
            "skor_akhir_standar": round(skor_akhir_standar, 4),
            "status": status
        })

    # --- Tahap 4: Penambahan Ranking Ganda (Logika yang Benar) ---
    hasil_saw_sorted = sorted(hasil_akhir, key=lambda x: x['skor_akhir_saw'], reverse=True)
    for i, item in enumerate(hasil_saw_sorted):
        item['ranking_saw'] = i + 1

    hasil_standar_sorted = sorted(hasil_akhir, key=lambda x: x['skor_akhir_standar'], reverse=True)
    standar_rank_map = {item['npm']: i + 1 for i, item in enumerate(hasil_standar_sorted)}

    for item in hasil_saw_sorted:
        item['ranking_standar'] = standar_rank_map.get(item['npm'])

    # --- Tahap 5: Penyimpanan Hasil ---
    hasil_collection = app.db.hasil_penilaian_saw
    hasil_collection.delete_many({})
    if hasil_saw_sorted:
        hasil_collection.insert_many(hasil_saw_sorted)

    # --- Tahap 6: Update Status Jadwal ---
    jadwal_collection = app.db.jadwal_saw
    jadwal_collection.update_one({"job_id": job_id}, {"$set": {"status": True}})
    print(f"Status untuk job {job_id} telah diupdate menjadi True.")
    
    # --- Tahap 7: Notifikasi Admin ---
    admin = app.db.admins.find_one({"username": "admin"})
    if admin and admin.get("email"):
        send_admin_notification_email(admin['email'], period_name, mail_config)
            
    print(f"--- Tugas Terjadwal (ID: {job_id}) Selesai ---")