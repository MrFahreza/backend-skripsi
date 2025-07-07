# backend/app/login/routes.py

from flask import request, jsonify, current_app
from bson.objectid import ObjectId
from . import login_bp
from werkzeug.security import check_password_hash, generate_password_hash
import jwt
from datetime import datetime, timedelta, timezone
from ..utils.decorators import token_required
from ..utils.password_utils import generate_new_password, send_new_password_email

# --- Endpoint untuk melakukan proses login ---
@login_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"code": 400, "message": "Username dan password dibutuhkan"}), 400
    
    username = data['username']
    password = data['password']
    admins_collection = current_app.db.admins
    admin_in_db = admins_collection.find_one({'username': username})

    if not admin_in_db:
        return jsonify({"code": 404, "message": "Username tidak ditemukan"}), 404

    if not check_password_hash(admin_in_db['password'], password):
        return jsonify({"code": 401, "message": "Password salah"}), 401

    # --- Bagian untuk membuat token jika login berhasil ---
    try:
        # Siapkan payload untuk token
        payload = {
            'exp': datetime.now(timezone.utc) + timedelta(hours=4), # Expired dalam 4 jam
            'iat': datetime.now(timezone.utc),                      # Waktu token dibuat
            'sub': str(admin_in_db['_id'])                          # Subject token (user id)
        }
        
        # Generate token
        token = jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        
        return jsonify({
            "code": 200,
            "message": "Login berhasil!",
            "token": token
        }), 200

    except Exception as e:
        return jsonify({"code": 500, "message": f"Gagal membuat token: {e}"}), 500


# --- Endpoint untuk melakukan reset password ---
@login_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    if not data or not data.get('username'):
        return jsonify({"code": 400, "message": "Username dibutuhkan"}), 400
    username = data['username']
    admins_collection = current_app.db.admins
    admin_user = admins_collection.find_one({"username": username})
    if not admin_user:
        return jsonify({"code": 404, "message": "Username tidak ditemukan"}), 404
    new_plain_password = generate_new_password()
    new_hashed_password = generate_password_hash(new_plain_password)
    admins_collection.update_one(
        {"_id": admin_user["_id"]},
        {"$set": {"password": new_hashed_password}}
    )
    mail_config = {
        "MAIL_SERVER": current_app.config['MAIL_SERVER'],
        "MAIL_PORT": current_app.config['MAIL_PORT'],
        "MAIL_USERNAME": current_app.config['MAIL_USERNAME'],
        "MAIL_PASSWORD": current_app.config['MAIL_PASSWORD']
    }
    email_sent = send_new_password_email(
        admin_user['email'], 
        new_plain_password, 
        mail_config
    )
    if email_sent:
        return jsonify({
            "code": 200,
            "message": "Password baru telah dikirim ke email Anda."
        }), 200
    else:
        return jsonify({
            "code": 500,
            "message": "Gagal mengirim email, silakan coba lagi."
        }), 500

# --- Endpoint untuk melakukan perubahan password ---
@login_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user_id):
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return jsonify({"code": 400, "message": "Password lama dan baru dibutuhkan"}), 400

    admins_collection = current_app.db.admins
    admin_user = admins_collection.find_one({"_id": ObjectId(current_user_id)})

    if not admin_user:
        return jsonify({"code": 404, "message": "User tidak ditemukan"}), 404
    if not check_password_hash(admin_user['password'], old_password):
        return jsonify({"code": 401, "message": "Password lama salah"}), 401
    new_hashed_password = generate_password_hash(new_password)
    admins_collection.update_one(
        {"_id": ObjectId(current_user_id)},
        {"$set": {"password": new_hashed_password}}
    )

    return jsonify({"code": 200, "message": "Password berhasil diubah"}), 200

# --- Endpoint untuk melakukan perubahan email admin ---
@login_bp.route('/change-email', methods=['POST'])
@token_required
def change_email(current_user_id):
    data = request.get_json()
    new_email = data.get('new_email')
    password = data.get('password')
    if not new_email or not password:
        return jsonify({"code": 400, "message": "Email baru dan password dibutuhkan"}), 400
    admins_collection = current_app.db.admins
    admin_user = admins_collection.find_one({"_id": ObjectId(current_user_id)})
    if not admin_user:
        return jsonify({"code": 404, "message": "User tidak ditemukan"}), 404
    if not check_password_hash(admin_user['password'], password):
        return jsonify({"code": 401, "message": "Password salah, perubahan email dibatalkan"}), 401
    admins_collection.update_one(
        {"_id": ObjectId(current_user_id)},
        {"$set": {"email": new_email}}
    )
    return jsonify({"code": 200, "message": f"Email berhasil diubah menjadi {new_email}"}), 200
