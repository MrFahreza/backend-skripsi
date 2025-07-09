from flask import request, jsonify, current_app
from pymongo import UpdateOne
import pandas as pd
from datetime import datetime, timezone # Import datetime
from . import mahasiswa_bp
from ..utils.decorators import token_required
import os
import re

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
        # 1. Validasi Format File
        filename, file_extension = os.path.splitext(file.filename)
        if file_extension not in ['.xlsx', '.csv']:
            return jsonify({"code": 400, "message": "Format file tidak didukung. Harap unggah .xlsx atau .csv"}), 400
        
        if file_extension == '.xlsx':
            df = pd.read_excel(file, dtype=str) # Baca semua sebagai string dulu
        else:
            df = pd.read_csv(file, dtype=str)

        # 2. Validasi Urutan dan Nama Kolom
        df.columns = df.columns.str.strip().str.lower()
        expected_columns = ['npm', 'nama', 'email', 'semester']
        if list(df.columns) != expected_columns:
            return jsonify({
                "code": 400,
                "message": f"Format kolom tidak sesuai. Harap gunakan urutan: {', '.join(expected_columns)}"
            }), 400

        mahasiswa_collection = current_app.db.mahasiswa
        existing_npm = {m['npm'] for m in mahasiswa_collection.find({}, {'npm': 1})}
        existing_emails = {m['email'] for m in mahasiswa_collection.find({}, {'email': 1})}
        
        errors = []
        operations = []
        now = datetime.now(timezone.utc)
        seen_in_file = {'npm': set(), 'email': set()}
        
        # Regex untuk validasi email
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        for index, row in df.iterrows():
            is_valid_row = True
            
            npm = row.get('npm')
            nama = row.get('nama')
            email = row.get('email')
            semester = row.get('semester')

            # 3. Validasi Format Data per Baris
            if not (npm and str(npm).isdigit()):
                errors.append(f"Baris {index + 2}: Kolom 'npm' harus berupa angka.")
                is_valid_row = False
            
            if not (email and re.match(email_regex, str(email))):
                errors.append(f"Baris {index + 2}: Kolom 'email' tidak memiliki format yang valid.")
                is_valid_row = False

            try:
                semester_val = int(semester)
                if not (1 <= semester_val <= 14):
                    errors.append(f"Baris {index + 2}: Kolom 'semester' harus bernilai antara 1 dan 14.")
                    is_valid_row = False
            except (ValueError, TypeError):
                errors.append(f"Baris {index + 2}: Kolom 'semester' harus berupa angka.")
                is_valid_row = False

            # 4. Validasi Duplikasi (jika data valid)
            if is_valid_row:
                if npm in existing_npm:
                    errors.append(f"Baris {index + 2}: NPM {npm} sudah ada di database.")
                    is_valid_row = False
                if email in existing_emails:
                    errors.append(f"Baris {index + 2}: Email {email} sudah ada di database.")
                    is_valid_row = False
                if npm in seen_in_file['npm']:
                    errors.append(f"Baris {index + 2}: NPM {npm} duplikat di dalam file.")
                    is_valid_row = False
                if email in seen_in_file['email']:
                    errors.append(f"Baris {index + 2}: Email {email} duplikat di dalam file.")
                    is_valid_row = False
            
            # Jika ada error apa pun di baris ini, lewati
            if not is_valid_row:
                continue
            
            # Jika lolos semua validasi, proses data
            seen_in_file['npm'].add(npm)
            seen_in_file['email'].add(email)
            doc = row.to_dict()
            operations.append(UpdateOne({"npm": npm}, {"$set": {**doc, "updated_at": now}, "$setOnInsert": {"_id": npm, "created_at": now}}, upsert=True))

        inserted_count = 0
        if operations:
            result = mahasiswa_collection.bulk_write(operations)
            inserted_count = result.upserted_count

        return jsonify({
            "code": 200, 
            "message": f"Proses impor selesai. Berhasil menambahkan {inserted_count} data.",
            "data_berhasil_ditambahkan": inserted_count,
            "catatan_error_data_dilewati": errors
        }), 200

    except Exception as e:
        return jsonify({"code": 500, "message": f"Gagal memproses file: {e}"}), 500

