# backend/app/utils/email_utils.py

import smtplib
from email.mime.text import MIMEText

def send_saw_warning_email(recipient_email, student_name, weak_criteria, mail_config):
    """Mengirim email peringatan hasil penilaian SAW."""
    subject = "Peringatan Hasil Penilaian Kinerja Mahasiswa"

    # Buat daftar kriteria yang lemah dalam format list
    criteria_list = "\n".join([f"- {item}" for item in weak_criteria])

    body = f"""
    Yth. {student_name},

    Berdasarkan hasil pengawasan yang kami lakukan dari kinerja anda selama ini.
    
    Kami informasikan bahwa hasil penilaian kinerja Anda untuk periode ini berada di bawah standar yang ditetapkan (dibawah 70).

    Berikut adalah kriteria yang perlu Anda tingkatkan:
{criteria_list}

    Kami mendorong Anda untuk lebih fokus dan meningkatkan kinerja pada kriteria di atas pada periode selanjutnya.
    Jika Anda memerlukan diskusi lebih lanjut, silakan hubungi bagian kemahasiswaan, Ketua Program Studi atau dosen wali.

    Terima kasih atas perhatian Anda.

    Hormat kami,
    Sistem Pengawasan Mahasiswa KIP-K
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
        print(f"Email peringatan berhasil dikirim ke {student_name} ({recipient_email})")
        return True
    except Exception as e:
        print(f"Gagal mengirim email peringatan ke {recipient_email}: {e}")
        return False

def send_admin_notification_email(admin_email, period_name, mail_config):
    """Mengirim email notifikasi ke admin setelah perhitungan otomatis."""
    subject = f"Notifikasi: Perhitungan SAW Periode {period_name} Selesai"
    body = f"""
    Halo Admin,

    Sistem telah berhasil menjalankan perhitungan dan perangkingan SAW secara otomatis untuk periode {period_name}.

    Silakan login ke sistem untuk melihat hasil selengkapnya.

    Terima kasih.

    Sistem Pengawasan Mahasiswa KIP-K (Otomatis)
    """
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = mail_config['MAIL_USERNAME']
    msg['To'] = admin_email

    try:
        with smtplib.SMTP(mail_config['MAIL_SERVER'], mail_config['MAIL_PORT']) as server:
            server.starttls()
            server.login(mail_config['MAIL_USERNAME'], mail_config['MAIL_PASSWORD'])
            server.send_message(msg)
        print(f"Email notifikasi admin berhasil dikirim ke {admin_email}")
        return True
    except Exception as e:
        print(f"Gagal mengirim email notifikasi admin: {e}")
        return False