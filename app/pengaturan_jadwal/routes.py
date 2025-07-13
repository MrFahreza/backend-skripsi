# backend/app/pengaturan_jadwal/routes.py

from flask import request, jsonify, current_app
from datetime import datetime
from apscheduler.jobstores.base import JobLookupError
from ..utils.decorators import token_required
from ..hasil_penilaian_saw.task import scheduled_saw_task

from . import jadwal_bp

# --- Endpoint untuk MELIHAT semua jadwal yang aktif ---
@jadwal_bp.route('/', methods=['GET'])
@token_required
def get_jobs(current_user_id):
    scheduler = current_app.scheduler.scheduler 
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'trigger': str(job.trigger),
            # --- PERUBAHAN DI SINI: Gunakan getattr untuk menghindari error ---
            'next_run_time': str(getattr(job, 'next_run_time', 'Telah Selesai / Tidak Ada'))
        })
    return jsonify({"code": 200, "data": jobs}), 200

# --- Endpoint untuk MEMBUAT jadwal baru ---
@jadwal_bp.route('/', methods=['POST'])
@token_required
def add_job(current_user_id):
    scheduler = current_app.scheduler.scheduler 
    data = request.get_json()
    run_date_str = data.get('run_date')
    period_name = data.get('period_name')

    if not run_date_str or not period_name:
        return jsonify({"code": 400, "message": "run_date dan period_name dibutuhkan"}), 400

    try:
        run_date = datetime.fromisoformat(run_date_str)
    except ValueError:
        return jsonify({"code": 400, "message": "Format tanggal tidak valid. Gunakan YYYY-MM-DDTHH:MM"}), 400
    
    job_id = f"saw_calc_{period_name.replace(' ', '_').lower()}"
    
    try:
        scheduler.add_job(
            id=job_id,
            func=scheduled_saw_task,
            trigger='date',
            run_date=run_date,
            args=[current_app._get_current_object(), period_name]
        )
        return jsonify({"code": 201, "message": f"Jadwal untuk '{period_name}' berhasil dibuat pada {run_date_str}"}), 201
    except Exception as e:
        return jsonify({"code": 500, "message": f"Gagal menambahkan jadwal: {e}"}), 500

# --- Endpoint untuk MENGHAPUS jadwal ---
@jadwal_bp.route('/<job_id>', methods=['DELETE'])
@token_required
def remove_job(current_user_id, job_id):
    scheduler = current_app.scheduler.scheduler 
    try:
        scheduler.remove_job(job_id)
        return jsonify({"code": 200, "message": f"Jadwal dengan ID '{job_id}' berhasil dihapus."}), 200
    except JobLookupError:
        return jsonify({"code": 404, "message": f"Jadwal dengan ID '{job_id}' tidak ditemukan."}), 404
    except Exception as e:
        return jsonify({"code": 500, "message": f"Gagal menghapus jadwal: {e}"}), 500