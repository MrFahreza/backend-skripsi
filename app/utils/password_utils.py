# backend/app/utils/password_utils.py

import string
import random
import smtplib
from email.mime.text import MIMEText

def generate_new_password(length=12):
    """Menghasilkan password acak yang aman."""
    characters = string.ascii_uppercase + string.digits
    new_password = ''.join(random.choice(characters) for i in range(length))
    return new_password

def send_new_password_email(recipient_email, new_password, mail_config):
    """Mengirim email berisi password baru."""
    subject = "Permintaan Atur Ulang Password Anda"
    body = f"""
    Halo Admin,

    Anda telah meminta untuk mengatur ulang password Anda.
    Password baru Anda adalah: {new_password}

    Harap segera login menggunakan password ini dan simpan di tempat yang aman.
    Abaikan email ini jika Anda tidak merasa meminta perubahan password.

    Terima kasih.
    """
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = mail_config['MAIL_USERNAME']
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP(mail_config['MAIL_SERVER'], mail_config['MAIL_PORT']) as server:
            server.starttls()
            server.login(mail_config['MAIL_USERNAME'], mail_config['MAIL_PASSWORD'])
            server.send_message(msg)
        print(f"Email reset password berhasil dikirim ke {recipient_email}")
        return True
    except Exception as e:
        print(f"Gagal mengirim email: {e}")
        return False