# backend/app/utils/email_utils.py

import smtplib
from email.mime.text import MIMEText

def send_saw_warning_email(recipient_email, student_name, weak_criteria, assessment_data, mail_config):
    """Mengirim email peringatan hasil penilaian SAW yang menyertakan detail nilai."""
    subject = "Peringatan Hasil Penilaian Kinerja Mahasiswa"
    
    criteria_list = "\n".join([f"- {item}" for item in weak_criteria])
    
    body = f"""
    Yth. {student_name},

    Kami informasikan bahwa hasil penilaian kinerja Anda untuk periode ini berada di bawah standar yang ditetapkan.
    Berikut adalah rincian penilaian dan kriteria yang perlu Anda tingkatkan:

    Rincian Penilaian Anda:
    - Keaktifan Organisasi: {assessment_data.get('keaktifan_organisasi', 0)}
    - IPK: {assessment_data.get('ipk', 0)}
    - Persentase Kehadiran: {assessment_data.get('persentase_kehadiran', 0) * 100}%

    Kriteria yang Perlu Ditingkatkan:
    {criteria_list}

    Kami mendorong Anda untuk lebih fokus dan meningkatkan kinerja pada kriteria di atas pada periode selanjutnya.
    Jika Anda memerlukan diskusi lebih lanjut, silakan hubungi bagian kemahasiswaan.

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

def send_saw_congrats_email(recipient_email, student_name, assessment_data, mail_config):
    """Mengirim email ucapan selamat hasil penilaian SAW."""
    subject = "Informasi Hasil Penilaian Kinerja Mahasiswa"
    
    body = f"""
    Yth. {student_name},

    Selamat! Hasil penilaian kinerja Anda untuk periode ini telah memenuhi standar yang ditetapkan.
    Terus pertahankan dan tingkatkan prestasi Anda.

    Berikut adalah rincian penilaian Anda:
    - Keaktifan Organisasi: {assessment_data.get('keaktifan_organisasi', 0)}
    - IPK: {assessment_data.get('ipk', 0)}
    - Persentase Kehadiran: {assessment_data.get('persentase_kehadiran', 0) * 100}%

    Terima kasih atas dedikasi dan kerja keras Anda.

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
        print(f"Email ucapan selamat berhasil dikirim ke {student_name} ({recipient_email})")
        return True
    except Exception as e:
        print(f"Gagal mengirim email ucapan selamat ke {recipient_email}: {e}")
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