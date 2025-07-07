from flask import jsonify, current_app, send_file
from io import BytesIO
import pandas as pd
from . import saw_bp
from ..utils.decorators import token_required
from ..utils.email_utils import send_saw_warning_email
import numpy as np

# --- Konfigurasi Bobot Kriteria ---
BOBOT_SAW = {
    "w1": 0.25, # Keaktifan Organisasi
    "w2": 0.35, # IPK
    "w3": 0.40  # Persentase Kehadiran
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
    mahasiswa_collection = current_app.db.data_mahasiswa
    
    # 1. Ambil semua data penilaian yang ada
    all_penilaian = list(penilaian_collection.find({}))
    if not all_penilaian:
        return jsonify({"code": 404, "message": "Tidak ada data penilaian untuk dihitung"}), 404
    student_emails = {m['npm']: m['email'] for m in mahasiswa_collection.find({}, {'npm': 1, 'email': 1})}

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
    # Karena semua kriteria adalah benefit, cari nilai MAX dari setiap kolom
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
    mail_config = {
        "MAIL_SERVER": current_app.config['MAIL_SERVER'],
        "MAIL_PORT": current_app.config['MAIL_PORT'],
        "MAIL_USERNAME": current_app.config['MAIL_USERNAME'],
        "MAIL_PASSWORD": current_app.config['MAIL_PASSWORD']
    }

    for i, item_r in enumerate(matriks_r):
        skor_akhir = (
            (item_r['r1_normalized'] * BOBOT_SAW['w1']) +
            (item_r['r2_normalized'] * BOBOT_SAW['w2']) +
            (item_r['r3_normalized'] * BOBOT_SAW['w3'])
        )
        
        status = "Standar Terpenuhi"
        if skor_akhir < 0.7:
            status = "Perlu Tindakan dan Peringatan"
            kriteria_lemah = []
            item_x = matriks_x[i]
            if item_x['c1_rated'] <= 2: kriteria_lemah.append("Keaktifan Organisasi")
            if item_x['c2_rated'] <= 2: kriteria_lemah.append("IPK")
            if item_x['c3_rated'] <= 2: kriteria_lemah.append("Persentase Kehadiran")
            if kriteria_lemah:
                student_email = student_emails.get(item_r['npm'])
                if student_email:
                    send_saw_warning_email(student_email, item_r['nama'], kriteria_lemah, mail_config)

        hasil_akhir.append({
            "npm": item_r['npm'],
            "nama": item_r['nama'],
            "skor_akhir_saw": round(skor_akhir, 4),
            "status": status
        })
    
    # --- Tahap 4: Simpan Hasil ke Database ---
    hasil_akhir_sorted = sorted(hasil_akhir, key=lambda x: x['skor_akhir_saw'], reverse=True)
    hasil_collection = current_app.db.hasil_penilaian_saw
    hasil_collection.delete_many({})
    if hasil_akhir_sorted:
        hasil_collection.insert_many(hasil_akhir_sorted)
    return jsonify({"code": 200, "message": "Perhitungan SAW berhasil dan hasil telah disimpan."}), 200

# --- Endpoint untuk Melihat Hasil Perhitungan SAW ---
@saw_bp.route('/', methods=['GET'])
@token_required
def get_saw_results(current_user_id):
    hasil_collection = current_app.db.hasil_penilaian_saw
    results = list(hasil_collection.find({}, {'_id': 0}))
    if not results:
        return jsonify({"code": 404, "message": "Hasil perhitungan belum ada. Silakan picu perhitungan terlebih dahulu."}), 404
    return jsonify({"code": 200, "data": results}), 200

# --- Endpoint untuk export hasil perhitungan kedalam file excel ---
@saw_bp.route('/export', methods=['GET'])
@token_required
def export_saw_results(current_user_id):
    hasil_collection = current_app.db.hasil_penilaian_saw
    results = list(hasil_collection.find({}, {'_id': 0}))
    if not results:
        return jsonify({"code": 404, "message": "Tidak ada data hasil perhitungan untuk diekspor."}), 404
    df = pd.DataFrame(results)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Hasil_SAW')
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='hasil_penilaian_saw.xlsx'
    )