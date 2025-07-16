import traceback
from flask import request, jsonify, current_app
from datetime import datetime, timezone
import pytz
from apscheduler.jobstores.base import JobLookupError
from ..utils.decorators import token_required
from ..hasil_penilaian_saw.task import scheduled_saw_task
from bson.objectid import ObjectId

from . import jadwal_bp

# --- Endpoint untuk MELIHAT semua jadwal dari database kita ---
@jadwal_bp.route('/', methods=['GET'])
@token_required
def get_jobs(current_user_id):
    jadwal_collection = current_app.db.jadwal_saw
    jobs = list(jadwal_collection.find({}))
    local_tz = pytz.timezone('Asia/Jakarta')
    
    for job in jobs:
        # --- PERUBAHAN DI SINI ---
        # Ambil waktu UTC dari DB
        utc_run_date = job['run_date'].replace(tzinfo=pytz.utc)
        # Konversi ke waktu lokal (WIB)
        local_run_date = utc_run_date.astimezone(local_tz)

        job['_id'] = str(job['_id'])
        # Tampilkan waktu yang sudah dikonversi
        job['run_date'] = local_run_date.isoformat() 
        job['created_at'] = job['created_at'].isoformat()
        
    return jsonify({"code": 200, "data": jobs}), 200

# --- Endpoint untuk MEMBUAT jadwal baru ---
@jadwal_bp.route('/', methods=['POST'])
@token_required
def add_job(current_user_id):
    data = request.get_json()
    run_date_str = data.get('run_date')
    period_name = data.get('period_name')

    if not run_date_str or not period_name:
        return jsonify({"code": 400, "message": "run_date dan period_name dibutuhkan"}), 400

    try:
        local_tz = pytz.timezone('Asia/Jakarta')
        naive_run_date = datetime.fromisoformat(run_date_str)
        aware_run_date = local_tz.localize(naive_run_date)
        if aware_run_date < datetime.now(local_tz):
            return jsonify({"code": 400, "message": "Waktu jadwal tidak boleh di masa lalu."}), 400
    except ValueError:
        return jsonify({"code": 400, "message": "Format tanggal tidak valid. Gunakan YYYY-MM-DDTHH:MM"}), 400

    scheduler = current_app.scheduler
    job_id = f"saw_calc_{period_name.replace(' ', '_').lower()}_{int(aware_run_date.timestamp())}"
    jadwal_collection = current_app.db.jadwal_saw

    # --- LOG DIAGNOSTIK ---
    print("\n--- DEBUG: PROSES PENAMBAHAN JADWAL BARU ---")
    print(f"Scheduler Instance: {scheduler}")
    print(f"Apakah scheduler berjalan? {scheduler.running}")
    # --- PERBAIKAN DI BARIS INI ---
    print(f"Jobstore yang terkonfigurasi: {current_app.config.get('SCHEDULER_JOBSTORES')}")
    print(f"ID Job yang akan dibuat: {job_id}")
    print(f"Waktu eksekusi (aware): {aware_run_date}")
    # ------------------------------------------------

    try:
        jadwal_collection.insert_one({
            "job_id": job_id, "period_name": period_name,
            "run_date": aware_run_date, "status": False,
            "created_at": datetime.now(timezone.utc)
        })

        scheduler.add_job(
            id=job_id,
            func='app.hasil_penilaian_saw.task:scheduled_saw_task',
            name=period_name,
            trigger='date',
            run_date=aware_run_date,
            args=[period_name, job_id]
        )
        
        print(f"--- DEBUG: Panggilan scheduler.add_job() BERHASIL tanpa exception ---")
        job_in_scheduler = scheduler.get_job(job_id)
        print(f"--- DEBUG: Hasil verifikasi get_job({job_id}): {job_in_scheduler} ---")

        return jsonify({"code": 201, "message": f"Jadwal untuk '{period_name}' berhasil dibuat."}), 201
    
    except Exception as e:
        print("\n!!! TERJADI EXCEPTION SAAT MENAMBAHKAN JADWAL !!!")
        traceback.print_exc()
        jadwal_collection.delete_one({"job_id": job_id})
        return jsonify({"code": 500, "message": f"Gagal menambahkan jadwal: {e}"}), 500


# --- Endpoint untuk MENGHAPUS jadwal ---
@jadwal_bp.route('/<job_id>', methods=['DELETE'])
@token_required
def remove_job(current_user_id, job_id):
    scheduler = current_app.scheduler.scheduler
    jadwal_collection = current_app.db.jadwal_saw
    
    # 1. Hapus dari scheduler
    try:
        scheduler.remove_job(job_id)
    except JobLookupError:
        print(f"Job {job_id} tidak ditemukan di scheduler (mungkin sudah berjalan). Tetap lanjut hapus dari DB.")
    
    # 2. Hapus dari database kita
    result = jadwal_collection.delete_one({"job_id": job_id})
    
    if result.deleted_count > 0:
        return jsonify({"code": 200, "message": f"Jadwal '{job_id}' berhasil dihapus."}), 200
    else:
        return jsonify({"code": 404, "message": f"Jadwal '{job_id}' tidak ditemukan di database."}), 404