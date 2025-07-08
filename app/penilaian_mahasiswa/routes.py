# backend/app/penilaian_mahasiswa/routes.py

from flask import request, jsonify, current_app
from pymongo import UpdateOne
import pandas as pd
from datetime import datetime, timezone
from . import penilaian_bp
from ..utils.decorators import token_required

# --- Helper Function untuk Menghitung Keaktifan Organisasi ---
def _calculate_keaktifan(data):
    """Menghitung skor keaktifan berdasarkan bobot yang ditentukan."""
    jabatan = float(data.get('jabatan_struktur', 0))
    keterlibatan = float(data.get('keterlibatan_program_kerja', 0))
    kinerja = float(data.get('penilaian_kinerja', 0))
    lomba = float(data.get('keikutsertaan_lomba', 0))
    
    # Rumus perhitungan
    skor = (0.2 * jabatan) + (0.45 * keterlibatan) + (0.15 * kinerja) + (0.2 * lomba)
    return round(skor, 2)

# --- Endpoint untuk Menambahkan Penilaian (Create) ---
@penilaian_bp.route('/', methods=['POST'])
@token_required
def add_penilaian(current_user_id):
    data = request.get_json()
    npm = data.get('npm')

    if not npm:
        return jsonify({"code": 400, "message": "NPM mahasiswa dibutuhkan"}), 400
    mahasiswa_collection = current_app.db.mahasiswa
    penilaian_collection = current_app.db.penilaian_mahasiswa
    mahasiswa_data = mahasiswa_collection.find_one({"npm": npm})
    if not mahasiswa_data:
        return jsonify({"code": 404, "message": f"Mahasiswa dengan NPM {npm} tidak ditemukan"}), 404
    if penilaian_collection.find_one({"npm": npm}):
        return jsonify({"code": 409, "message": f"Mahasiswa dengan NPM {npm} sudah memiliki data penilaian"}), 409

    # Hitung skor keaktifan
    data['keaktifan_organisasi'] = _calculate_keaktifan(data)
    
    now = datetime.now(timezone.utc)
    
    # Siapkan dokumen untuk disimpan
    penilaian_doc = {
        "npm": npm,
        "nama": mahasiswa_data['nama'],
        "semester": mahasiswa_data['semester'],
        "jabatan_struktur": data.get('jabatan_struktur'),
        "keterlibatan_program_kerja": data.get('keterlibatan_program_kerja'),
        "penilaian_kinerja": data.get('penilaian_kinerja'),
        "keikutsertaan_lomba": data.get('keikutsertaan_lomba'),
        "keaktifan_organisasi": data['keaktifan_organisasi'],
        "ipk": data.get('ipk'),
        "persentase_kehadiran": data.get('persentase_kehadiran'),
        "created_at": now,
        "updated_at": now
    }

    penilaian_collection.insert_one(penilaian_doc)
    return jsonify({"code": 201, "message": "Data penilaian berhasil ditambahkan"}), 201

# --- Endpoint untuk Melihat Semua Penilaian (Read) ---
@penilaian_bp.route('/', methods=['GET'])
@token_required
def get_all_penilaian(current_user_id):
    penilaian_collection = current_app.db.penilaian_mahasiswa
    all_penilaian = list(penilaian_collection.find())
    for p in all_penilaian:
        p['_id'] = str(p['_id'])
    return jsonify({"code": 200, "data": all_penilaian}), 200

# --- Endpoint untuk Mengubah Penilaian (Update) ---
@penilaian_bp.route('/<npm>', methods=['PUT'])
@token_required
def update_penilaian(current_user_id, npm):
    data = request.get_json()
    penilaian_collection = current_app.db.penilaian_mahasiswa
    existing_data = penilaian_collection.find_one({"npm": npm})
    if not existing_data:
        return jsonify({"code": 404, "message": "Data penilaian tidak ditemukan"}), 404
    updated_data = {**existing_data, **data}
    data['keaktifan_organisasi'] = _calculate_keaktifan(updated_data)
    data['updated_at'] = datetime.now(timezone.utc)

    penilaian_collection.update_one({"npm": npm}, {"$set": data})
    return jsonify({"code": 200, "message": "Data penilaian berhasil diperbarui"}), 200

# --- Endpoint untuk Menghapus Penilaian (Delete) ---
@penilaian_bp.route('/<npm>', methods=['DELETE'])
@token_required
def delete_penilaian(current_user_id, npm):
    penilaian_collection = current_app.db.penilaian_mahasiswa
    result = penilaian_collection.delete_one({"npm": npm})
    if result.deleted_count == 0:
        return jsonify({"code": 404, "message": "Data penilaian tidak ditemukan"}), 404
    return jsonify({"code": 200, "message": "Data penilaian berhasil dihapus"}), 200

# --- Endpoint untuk Impor dari Excel ---
@penilaian_bp.route('/import', methods=['POST'])
@token_required
def import_penilaian_from_excel(current_user_id):
    file = request.files.get('file')
    if not file: return jsonify({"code": 400, "message": "Tidak ada file yang diunggah"})
    
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file, dtype={'npm': str})
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(file, dtype={'npm': str})
        else:
            return jsonify({"code": 400, "message": "Format file tidak didukung. Harap unggah .xlsx atau .csv"}), 400
        
        df.columns = df.columns.str.strip().str.lower()

        mahasiswa_collection = current_app.db.mahasiswa
        penilaian_collection = current_app.db.penilaian_mahasiswa
        
        all_mahasiswa_master = {m['npm']: m for m in mahasiswa_collection.find({})}
        
        operations = []
        errors = []
        now = datetime.now(timezone.utc)

        for index, row in df.iterrows():
            npm = row.get('npm')
            if npm not in all_mahasiswa_master:
                errors.append(f"Baris {index + 2}: NPM {npm} tidak ditemukan di data mahasiswa (dilewati).")
                continue
            mahasiswa_data = all_mahasiswa_master[npm]
            doc = row.to_dict()
            doc['keaktifan_organisasi'] = _calculate_keaktifan(doc)
            doc['nama'] = mahasiswa_data['nama']
            doc['semester'] = mahasiswa_data['semester']
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
        inserted_count = 0
        updated_count = 0
        if operations:
            result = penilaian_collection.bulk_write(operations)
            inserted_count = result.upserted_count
            updated_count = result.modified_count
        summary_message = f"Proses impor selesai. Berhasil menambahkan {inserted_count} data baru dan memperbarui {updated_count} data."

        return jsonify({
            "code": 200, 
            "message": summary_message,
            "details": {
                "data_ditambahkan": inserted_count,
                "data_diperbarui": updated_count,
                "data_dilewati_errors": errors
            }
        }), 200

    except Exception as e:
        return jsonify({"code": 500, "message": f"Gagal memproses file: {e}"}), 500