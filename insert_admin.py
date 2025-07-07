# backend/insert_admin.py

import os
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')

client = MongoClient(MONGO_URI)
db = client['admin_db']
admins_collection = db['admins']

admin_username = "admin"
admin_password = "admin"
# TAMBAHKAN EMAIL DI SINI
admin_email = "azerhafikzir@gmail.com" 

if admins_collection.find_one({'username': admin_username}):
    print(f"Admin dengan username '{admin_username}' sudah ada.")
else:
    hashed_password = generate_password_hash(admin_password)
    
    admin_document = {
        "username": admin_username,
        "password": hashed_password,
        "email": admin_email  # Tambahkan field email
    }
    
    admins_collection.insert_one(admin_document)
    print(f"Admin '{admin_username}' dengan email '{admin_email}' berhasil ditambahkan.")

client.close()