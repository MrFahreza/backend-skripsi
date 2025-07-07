# backend/app/hasil_penilaian_saw/routes.py

from flask import jsonify, current_app
from . import saw_bp
from ..utils.decorators import token_required
import numpy as np

# --- Konfigurasi Bobot Kriteria ---
BOBOT_SAW = {
    "c1": 0.25, # Keaktifan Organisasi
    "c2": 0.35, # IPK
    "c3": 0.40  # Persentase Kehadiran
}

# --- Helper Function untuk Rating Kecocokan ---
def _get_rating(c1, c2, c3):
    """Mengubah nilai kriteria asli menjadi skala rating 1-5."""
    # Rating C1: Keaktifan Organisasi
    if c1 == 5: r1 = 5
    elif c1 >= 3: r1 = 4
    elif c1 >= 2: r1 = 3
    elif c1 >= 1: r1 = 2
    else: r1 = 1
    
    # Rating C2: IPK
    if c2 == 4: r2 = 5
    elif c2 >= 3: r2 = 4
    elif c2 >= 2: r2 = 3
    elif c2 >= 1: r2 = 2
    else: r2 = 1
    
    # Rating C3: Persentase Kehadiran (diasumsikan 0-1)
    if c3 >= 1.0: r3 = 5
    elif c3 >= 0.9: r3 = 4
    elif c3 >= 0.8: r3 = 3
    elif c3 >= 0.7: r3 = 2
    else: r3 = 1
    
    return r1, r2, r3

# --- Endpoint untuk Memicu Perhitungan SAW ---
@saw_bp.route('/calculate', methods=['POST'])
@token_required
def calculate_saw(current_user_id):
    penilaian_collection = current_app.db.penilaian_mahasiswa
    
    # 1. Ambil semua data penilaian yang ada
    all_penilaian = list(penilaian_collection.find({}))
    if not all_penilaian:
        return jsonify({"code": 404, "message": "Tidak ada data penilaian untuk dihitung"}), 404

    # --- Tahap 1: Membuat Matriks Keputusan (X) dengan Rating Kecocokan ---
    matriks_x = []
    for p in all_penilaian:
        c1 = p.get('keaktifan_organisasi', 0)
        c2 = p.get('ipk', 0)
        c3 = p.get('persentase_kehadiran', 0)
        
        r1, r2, r3 = _get_rating(c1, c2, c3)
        
        matriks_x.append({
            "npm": p['npm'],
            "nama": p['nama'],
            "c1_rated": r1,
            "c2_rated": r2,
            "c3_rated": r3
        })
    
    # --- Tahap 2: Normalisasi Matriks ---
    # Karena semua kriteria adalah benefit, kita cari nilai MAX dari setiap kolom
    max_c1 = max(item['c1_rated'] for item in matriks_x)
    max_c2 = max(item['c2_rated'] for item in matriks_x)
    max_c3 = max(item['c3_rated'] for item in matriks_x)
    
    matriks_r = []
    for item in matriks_x:
        matriks_r.append({
            "npm": item['npm'],
            "nama": item['nama'],
            "r1_normalized": round(item['c1_rated'] / max_c1, 3),
            "r2_normalized": round(item['c2_rated'] / max_c2, 3),
            "r3_normalized": round(item['c3_rated'] / max_c3, 3)
        })

    # --- Tahap 3: Perangkingan ---
    hasil_akhir = []
    for item in matriks_r:
        skor_akhir = (
            (item['r1_normalized'] * BOBOT_SAW['c1']) +
            (item['r2_normalized'] * BOBOT_SAW['c2']) +
            (item['r3_normalized'] * BOBOT_SAW['c3'])
        )
        hasil_akhir.append({
            "npm": item['npm'],
            "nama": item['nama'],
            "skor_akhir_saw": round(skor_akhir, 4)
        })
    
    # Urutkan hasil dari yang tertinggi
    hasil_akhir_sorted = sorted(hasil_akhir, key=lambda x: x['skor_akhir_saw'], reverse=True)
    
    # --- Tahap 4: Simpan Hasil ke Database ---
    hasil_collection = current_app.db.hasil_penilaian_saw
    # Hapus hasil perhitungan lama sebelum menyimpan yang baru
    hasil_collection.delete_many({})
    # Simpan hasil perhitungan yang baru
    if hasil_akhir_sorted:
        hasil_collection.insert_many(hasil_akhir_sorted)

    return jsonify({"code": 200, "message": "Perhitungan SAW berhasil dan hasil telah disimpan."}), 200

# --- Endpoint untuk Melihat Hasil Perhitungan SAW ---
@saw_bp.route('/', methods=['GET'])
@token_required
def get_saw_results(current_user_id):
    hasil_collection = current_app.db.hasil_penilaian_saw
    # Ambil hasil yang sudah diurutkan dari database (field _id diabaikan)
    results = list(hasil_collection.find({}, {'_id': 0}))

    if not results:
        return jsonify({"code": 404, "message": "Hasil perhitungan belum ada. Silakan picu perhitungan terlebih dahulu."}), 404
        
    return jsonify({"code": 200, "data": results}), 200