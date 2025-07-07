# backend/run.py

from app import create_app

# Membuat instance aplikasi dari factory
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)