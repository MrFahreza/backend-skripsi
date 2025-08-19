# backend/app/penilaian_mahasiswa/routes.py

from flask import request, jsonify, current_app
from pymongo import UpdateOne
import pandas as pd
from datetime import datetime, timezone
from . import penilaian_bp
from ..utils.decorators import token_required
import os
import re

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

    # --- PERUBAHAN UTAMA: Konversi dan Validasi Persentase Kehadiran ---
    kehadiran_input = data.get('persentase_kehadiran')
    kehadiran_final = 0.0 # Nilai default jika tidak diisi

    if kehadiran_input is not None:
        try:
            kehadiran_float = float(kehadiran_input)
            # Validasi rentang nilai harus 0-100
            if not (0 <= kehadiran_float <= 100):
                return jsonify({"code": 400, "message": "Persentase kehadiran harus bernilai antara 0 dan 100."}), 400
            # Konversi dari skala 0-100 ke 0-1
            kehadiran_final = kehadiran_float / 100.0
        except (ValueError, TypeError):
            return jsonify({"code": 400, "message": "Persentase kehadiran harus berupa angka."}), 400
    # -----------------------------------------------------------------
    
    # Menyiapkan dokumen untuk disimpan
    penilaian_doc = {
        "npm": npm,
        "nama": mahasiswa_data['nama'],
        "semester": mahasiswa_data['semester'],
        "jabatan_struktur": data.get('jabatan_struktur'),
        "keterlibatan_program_kerja": data.get('keterlibatan_program_kerja'),
        "penilaian_kinerja": data.get('penilaian_kinerja'),
        "keikutsertaan_lomba": data.get('keikutsertaan_lomba'),
        "ipk": data.get('ipk'),
        "persentase_kehadiran": kehadiran_final, # Simpan nilai yang sudah dikonversi
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Hitung skor keaktifan organisasi menggunakan data yang sudah lengkap
    penilaian_doc['keaktifan_organisasi'] = _calculate_keaktifan(penilaian_doc)

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

    # --- PERUBAHAN: Konversi dan Validasi Persentase Kehadiran ---
    # Cek apakah field ini ada di dalam data yang dikirim untuk di-update
    if 'persentase_kehadiran' in data:
        kehadiran_input = data.get('persentase_kehadiran')
        if kehadiran_input is not None:
            try:
                kehadiran_float = float(kehadiran_input)
                # Validasi rentang nilai harus 0-100
                if not (0 <= kehadiran_float <= 100):
                    return jsonify({"code": 400, "message": "Persentase kehadiran harus bernilai antara 0 dan 100."}), 400
                
                # Update dictionary 'data' dengan nilai yang sudah dikonversi
                data['persentase_kehadiran'] = kehadiran_float / 100.0
            except (ValueError, TypeError):
                return jsonify({"code": 400, "message": "Persentase kehadiran harus berupa angka."}), 400
    # -----------------------------------------------------------------

    penilaian_collection = current_app.db.penilaian_mahasiswa
    existing_data = penilaian_collection.find_one({"npm": npm})
    if not existing_data:
        return jsonify({"code": 404, "message": "Data penilaian tidak ditemukan"}), 404
    
    # Gabungkan data lama dengan data baru yang sudah divalidasi/dikonversi
    updated_data = {**existing_data, **data}
    
    # Hitung ulang keaktifan dan set waktu update
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
    if not file:
        return jsonify({"code": 400, "message": "Tidak ada file yang diunggah"}), 400

    try:
        # --- Tahap 1: Validasi File dan Header ---
        filename, file_extension = os.path.splitext(file.filename)
        if file_extension not in ['.xlsx', '.csv']:
            return jsonify({"code": 400, "message": "Format file tidak didukung. Harap unggah .xlsx atau .csv"}), 400

        if file_extension == '.xlsx':
            df = pd.read_excel(file, dtype=str)
        else:
            df = pd.read_csv(file, dtype=str)

        df.columns = df.columns.str.strip().str.lower()
        
        actual_columns = set(df.columns)
        all_possible_columns = {
            'npm', 'jabatan_struktur', 'keterlibatan_program_kerja',
            'penilaian_kinerja', 'keikutsertaan_lomba', 'ipk', 'persentase_kehadiran'
        }

        if 'npm' not in actual_columns:
            return jsonify({"code": 400, "message": "File yang diunggah harus memiliki kolom 'npm'."}), 400

        unknown_columns = actual_columns - all_possible_columns
        if unknown_columns:
            return jsonify({
                "code": 400,
                "message": f"Ditemukan nama kolom yang tidak dikenal: {', '.join(unknown_columns)}"
            }), 400

        mahasiswa_collection = current_app.db.mahasiswa
        penilaian_collection = current_app.db.penilaian_mahasiswa
        all_mahasiswa_master = {m['npm']: m for m in mahasiswa_collection.find({})}

        operations = []
        errors = []
        now = datetime.now(timezone.utc)

        # --- Tahap 2: Validasi dan Penggabungan Data per Baris ---
        for index, row in df.iterrows():
            row_errors = []
            npm = row.get('npm')

            if not npm or not npm.isdigit() or npm not in all_mahasiswa_master:
                errors.append(f"Baris {index + 2}: NPM '{npm}' tidak valid atau tidak ditemukan (dilewati).")
                continue

            update_payload = {}
            for col in actual_columns:
                if col != 'npm' and pd.notna(row.get(col)) and str(row.get(col)).strip() != '':
                    val_str = str(row.get(col))
                    try:
                        val_float = float(val_str)
                        
                        if col in ['jabatan_struktur', 'keterlibatan_program_kerja', 'penilaian_kinerja', 'keikutsertaan_lomba'] and not (0 <= val_float <= 5):
                            row_errors.append(f"Kolom '{col}' ({val_str}) harus antara 0 dan 5.")
                        elif col == 'ipk' and not (0 <= val_float <= 4):
                            row_errors.append(f"Kolom 'ipk' ({val_str}) harus antara 0 dan 4.")
                        elif col == 'persentase_kehadiran':
                            if not (0 <= val_float <= 100):
                                row_errors.append(f"Kolom 'persentase_kehadiran' ({val_str}) harus antara 0 dan 100.")
                            else:
                                update_payload[col] = val_float / 100.0 # Konversi ke 0-1
                        else:
                            update_payload[col] = val_float
                    except (ValueError, TypeError):
                        row_errors.append(f"Kolom '{col}' ({val_str}) harus berupa angka.")
            
            if row_errors:
                errors.append(f"Baris {index + 2} (NPM: {npm}): " + " | ".join(row_errors) + " (dilewati).")
                continue

            if not update_payload:
                continue

            existing_assessment = penilaian_collection.find_one({"npm": npm}) or {}
            merged_data = {**existing_assessment, **update_payload}
            merged_data['keaktifan_organisasi'] = _calculate_keaktifan(merged_data)
            
            final_doc = {
                "npm": npm, "nama": all_mahasiswa_master[npm]['nama'], "semester": all_mahasiswa_master[npm]['semester'],
                "jabatan_struktur": merged_data.get('jabatan_struktur', 0.0),
                "keterlibatan_program_kerja": merged_data.get('keterlibatan_program_kerja', 0.0),
                "penilaian_kinerja": merged_data.get('penilaian_kinerja', 0.0),
                "keikutsertaan_lomba": merged_data.get('keikutsertaan_lomba', 0.0),
                "keaktifan_organisasi": merged_data.get('keaktifan_organisasi', 0.0),
                "ipk": merged_data.get('ipk', 0.0),
                "persentase_kehadiran": merged_data.get('persentase_kehadiran', 0.0)
            }

            operations.append(UpdateOne({"npm": npm}, {"$set": final_doc, "$setOnInsert": {"created_at": now}}, upsert=True))

        # --- Tahap 3: Eksekusi Database dan Kirim Respons ---
        inserted_count = 0
        updated_count = 0
        if operations:
            result = penilaian_collection.bulk_write(operations)
            inserted_count = result.upserted_count
            updated_count = result.modified_count
            
        summary_message = f"Proses impor selesai. Berhasil menambahkan {inserted_count} data baru dan memperbarui {updated_count} data."

        return jsonify({
            "code": 200, "message": summary_message,
            "details": {
                "data_ditambahkan": inserted_count, "data_diperbarui": updated_count,
                "data_dilewati_errors": errors
            }
        }), 200

    except Exception as e:
        print(f"!!! ERROR SAAT IMPORT: {e}")
        return jsonify({"code": 500, "message": f"Gagal memproses file. Penyebab: {str(e)}"}), 500