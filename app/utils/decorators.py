# backend/app/utils/decorators.py

from functools import wraps
from flask import request, jsonify, current_app
import jwt

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Cek jika 'Authorization' header ada
        if 'Authorization' in request.headers:
            # Ambil token dari header (format: "Bearer <token>")
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"code": 401, "message": "Format token tidak benar"}), 401

        if not token:
            return jsonify({"code": 401, "message": "Token dibutuhkan"}), 401

        try:
            # Decode token menggunakan Secret Key
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['sub']
        except jwt.ExpiredSignatureError:
            return jsonify({"code": 401, "message": "Token telah expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"code": 401, "message": "Token tidak valid"}), 401

        # Kirim id user ke fungsi yang di-wrap
        return f(current_user_id, *args, **kwargs)
    return decorated