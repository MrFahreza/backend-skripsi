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
    penilaian_collection = current_app.db.penilaian_mahasiswa
    result = mahasiswa_collection.delete_one({"npm": npm})
    if result.deleted_count == 0:
        return jsonify({"code": 404, "message": "Data mahasiswa tidak ditemukan"}), 404
    penilaian_collection.delete_one({"npm": npm})
    return jsonify({"code": 200, "message": "Data mahasiswa dan data penilaian terkait berhasil dihapus"}), 200

# --- Endpoint untuk Impor dari Excel ---
@mahasiswa_bp.route('/import', methods=['POST'])
@token_required
def import_from_excel(current_user_id):
    file = request.files.get('file')
    if not file:
        return jsonify({"code": 400, "message": "Tidak ada file yang diunggah"}), 400

    try:
        df = pd.read_excel(file, dtype={'npm': str})
        mahasiswa_collection = current_app.db.mahasiswa
        existing_npm = {m['npm'] for m in mahasiswa_collection.find({}, {'npm': 1})}
        existing_emails = {m['email'] for m in mahasiswa_collection.find({}, {'email': 1})}
        errors = []
        operations = []
        now = datetime.now(timezone.utc)
        seen_in_file = {'npm': set(), 'email': set()}
        
        for index, row in df.iterrows():
            npm = row.get('npm')
            email = row.get('email')
            is_valid_row = True
            if npm in existing_npm:
                errors.append(f"Baris {index + 2}: NPM {npm} sudah ada di database (dilewati).")
                is_valid_row = False
            if email in existing_emails:
                errors.append(f"Baris {index + 2}: Email {email} sudah ada di database (dilewati).")
                is_valid_row = False
            if npm in seen_in_file['npm']:
                errors.append(f"Baris {index + 2}: NPM {npm} duplikat di dalam file Excel (dilewati).")
                is_valid_row = False
            if email in seen_in_file['email']:
                errors.append(f"Baris {index + 2}: Email {email} duplikat di dalam file Excel (dilewati).")
                is_valid_row = False

            seen_in_file['npm'].add(npm)
            seen_in_file['email'].add(email)

            if is_valid_row:
                doc = row.to_dict()
                operations.append(
                    UpdateOne(
                        {"npm": npm},
                        {
                            "$set": {**doc, "updated_at": now},
                            "$setOnInsert": {"_id": npm, "created_at": now}
                        },
                        upsert=True
                    )
                )
                
        inserted_count = 0
        if operations:
            result = mahasiswa_collection.bulk_write(operations)
            inserted_count = result.upserted_count

        return jsonify({
            "code": 200, 
            "message": "Proses impor selesai.",
            "data_berhasil_ditambahkan": inserted_count,
            "catatan_error_data_dilewati": errors
        }), 200

    except Exception as e:
        return jsonify({"code": 500, "message": f"Gagal memproses file: {e}"}), 500