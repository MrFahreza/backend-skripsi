from flask import request, jsonify, current_app
from pymongo import UpdateOne
import pandas as pd
from datetime import datetime, timezone # Import datetime
from . import mahasiswa_bp
from ..utils.decorators import token_required

# --- Endpoint untuk Menambahkan Mahasiswa (Create) ---
@mahasiswa_bp.route('/', methods=['POST'])
@token_required
def add_mahasiswa(current_user_id):
    data = request.get_json()
    npm = data.get('npm')
    email = data.get('email')
    mahasiswa_collection = current_app.db.mahasiswa
    if mahasiswa_collection.find_one({"npm": npm}):
        return jsonify({"code": 409, "message": "NPM sudah digunakan"}), 409
    if mahasiswa_collection.find_one({"email": email}):
        return jsonify({"code": 409, "message": "Email sudah digunakan"}), 409
    now = datetime.now(timezone.utc)
    mahasiswa_collection.insert_one({
        "_id": npm,
        "npm": npm,
        "nama": data.get('nama'),
        "email": email,
        "semester": data.get('semester'),
        "created_at": now,
        "updated_at": now
    })
    return jsonify({"code": 201, "message": "Data mahasiswa berhasil ditambahkan"}), 201

# --- Endpoint untuk Melihat Semua Mahasiswa (Read) ---
@mahasiswa_bp.route('/', methods=['GET'])
@token_required
def get_all_mahasiswa(current_user_id):
    mahasiswa_collection = current_app.db.mahasiswa
    all_mahasiswa = list(mahasiswa_collection.find({}, {'_id': 0}))
    return jsonify({"code": 200, "data": all_mahasiswa}), 200

# --- Endpoint untuk Mengubah Mahasiswa (Update) ---
@mahasiswa_bp.route('/<npm>', methods=['PUT'])
@token_required
def update_mahasiswa(current_user_id, npm):
    data = request.get_json()
    data['updated_at'] = datetime.now(timezone.utc)
    mahasiswa_collection = current_app.db.mahasiswa
    if 'email' in data:
        email_exists = mahasiswa_collection.find_one({"email": data['email'], "npm": {"$ne": npm}})
        if email_exists:
            return jsonify({"code": 409, "message": "Email sudah digunakan oleh mahasiswa lain"}), 409
    result = mahasiswa_collection.update_one({"npm": npm}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({"code": 404, "message": "Data mahasiswa tidak ditemukan"}), 404
    return jsonify({"code": 200, "message": "Data mahasiswa berhasil diperbarui"}), 200

# --- Endpoint untuk Menghapus Mahasiswa (Delete) ---
@mahasiswa_bp.route('/<npm>', methods=['DELETE'])
@token_required
def delete_mahasiswa(current_user_id, npm):
    mahasiswa_collection = current_app.db.mahasiswa
    result = mahasiswa_collection.delete_one({"npm": npm})
    if result.deleted_count == 0:
        return jsonify({"code": 404, "message": "Data mahasiswa tidak ditemukan"}), 404
    return jsonify({"code": 200, "message": "Data mahasiswa berhasil dihapus"}), 200

# --- Endpoint untuk Impor dari Excel ---
@mahasiswa_bp.route('/import', methods=['POST'])
@token_required
def import_from_excel(current_user_id):
    file = request.files.get('file')
    if not file: return jsonify({"code": 400, "message": "Tidak ada file yang diunggah"})
    try:
        df = pd.read_excel(file, dtype={'npm': str})
        mahasiswa_collection = current_app.db.mahasiswa
        existing_npm = {m['npm'] for m in mahasiswa_collection.find({}, {'npm': 1})}
        existing_emails = {m['email'] for m in mahasiswa_collection.find({}, {'email': 1})}
        errors = []
        operations = []
        now = datetime.now(timezone.utc)
        for index, row in df.iterrows():
            npm = row.get('npm')
            email = row.get('email')
            if npm in existing_npm: errors.append(f"Baris {index + 2}: NPM {npm} sudah ada.")
            if email in existing_emails: errors.append(f"Baris {index + 2}: Email {email} sudah ada.")
            doc = row.to_dict()
            operations.append(
                UpdateOne(
                    {"npm": npm},
                    {
                        "$set": {**doc, "updated_at": now},
                        "$setOnInsert": {"created_at": now}
                    },
                    upsert=True
                )
            )

        if errors:
            return jsonify({"code": 409, "message": errors}), 409
        if operations:
            result = mahasiswa_collection.bulk_write(operations)
            return jsonify({
                "code": 200, 
                "message": "Proses impor selesai",
                "inserted": result.upserted_count,
                "updated": result.modified_count
            }), 200
        return jsonify({"code": 200, "message": "Tidak ada data untuk diimpor"})
    except Exception as e:
        return jsonify({"code": 500, "message": f"Gagal memproses file: {e}"})