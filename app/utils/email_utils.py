# backend/app/utils/email_utils.py

import smtplib
from email.mime.text import MIMEText

# backend/app/utils/email_utils.py
import smtplib
from email.mime.text import MIMEText

def send_saw_warning_email(recipient_email, student_name, weak_criteria, assessment_data, mail_config, period_name):
    """Mengirim email peringatan hasil penilaian SAW yang diformat dengan HTML."""
    subject = "Peringatan Hasil Penilaian Kinerja Mahasiswa"
    
    criteria_list_html = "".join([f"<li>{item}</li>" for item in weak_criteria])
    
    body = f"""
    <html>
    <head></head>
    <body>
        <div style="font-family: 'Times New Roman', Times, serif; font-size: 18px; color: #333333;">
            <p>Yth. {student_name},</p>
            <p>Kami informasikan bahwa hasil penilaian kinerja Anda untuk periode <b>{period_name}</b> berada di bawah standar yang ditetapkan.<br>
            Berikut adalah rincian penilaian dan kriteria yang perlu Anda tingkatkan:</p>
            
            <h4 style="margin-bottom: 5px;">Rincian Penilaian Anda:</h4>
            <ul style="margin-top: 0;">
                <li><b>Keaktifan Organisasi:</b> {assessment_data.get('keaktifan_organisasi', 0)}</li>
                <li><b>IPK:</b> {assessment_data.get('ipk', 0)}</li>
                <li><b>Persentase Kehadiran:</b> {assessment_data.get('persentase_kehadiran', 0) * 100:.2f}%</li>
            </ul>

            <h4 style="margin-bottom: 5px;">Kriteria yang Perlu Ditingkatkan:</h4>
            <ul style="margin-top: 0;">
                {criteria_list_html}
            </ul>

            <p>Kami mendorong Anda untuk lebih fokus dan meningkatkan kinerja pada kriteria di atas pada periode selanjutnya.<br>
            Jika Anda memerlukan diskusi lebih lanjut, silakan hubungi bagian kemahasiswaan.</p>
            
            <p>Terima kasih atas perhatian Anda.</p>
            <br>
            <p>Hormat kami,<br>
            Sistem Pengawasan Mahasiswa KIP-K</p>
        </div>
    </body>
    </html>
    """
    
    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = mail_config['MAIL_USERNAME']
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP(mail_config['MAIL_SERVER'], mail_config['MAIL_PORT']) as server:
            server.starttls()
            server.login(mail_config['MAIL_USERNAME'], mail_config['MAIL_PASSWORD'])
            server.send_message(msg)
        print(f"Email peringatan HTML berhasil dikirim ke {student_name} ({recipient_email})")
        return True
    except Exception as e:
        print(f"Gagal mengirim email peringatan HTML ke {recipient_email}: {e}")
        return False

def send_saw_congrats_email(recipient_email, student_name, assessment_data, mail_config, period_name):
    """Mengirim email ucapan selamat hasil penilaian SAW yang diformat dengan HTML."""
    subject = "Informasi Hasil Penilaian Kinerja Mahasiswa"
    
    body = f"""
    <html>
    <head></head>
    <body>
        <div style="font-family: 'Times New Roman', Times, serif; font-size: 18px; color: #333333;">
            <p>Yth. {student_name},</p>
            <p><b>Selamat!</b> Hasil penilaian kinerja Anda untuk periode <b>{period_name}</b> telah <b>memenuhi standar</b> yang ditetapkan.<br>
            Terus pertahankan dan tingkatkan prestasi Anda.</p>
            
            <h4 style="margin-bottom: 5px;">Berikut adalah rincian penilaian Anda:</h4>
            <ul style="margin-top: 0;">
                <li><b>Keaktifan Organisasi:</b> {assessment_data.get('keaktifan_organisasi', 0)}</li>
                <li><b>IPK:</b> {assessment_data.get('ipk', 0)}</li>
                <li><b>Persentase Kehadiran:</b> {assessment_data.get('persentase_kehadiran', 0) * 100:.2f}%</li>
            </ul>

            <p>Terima kasih atas dedikasi dan kerja keras Anda.</p>
            <br>
            <p>Hormat kami,<br>
            Sistem Pengawasan Mahasiswa KIP-K</p>
        </div>
    </body>
    </html>
    """
    
    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = mail_config['MAIL_USERNAME']
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP(mail_config['MAIL_SERVER'], mail_config['MAIL_PORT']) as server:
            server.starttls()
            server.login(mail_config['MAIL_USERNAME'], mail_config['MAIL_PASSWORD'])
            server.send_message(msg)
        print(f"Email ucapan selamat HTML berhasil dikirim ke {student_name} ({recipient_email})")
        return True
    except Exception as e:
        print(f"Gagal mengirim email ucapan selamat HTML ke {recipient_email}: {e}")
        return False

def send_admin_notification_email(admin_email, period_name, mail_config):
    """Mengirim email notifikasi ke admin setelah perhitungan otomatis."""
    subject = f"Notifikasi: Perhitungan SAW Periode {period_name} Selesai"
    
    body = f"""
    <html>
    <head></head>
    <body style="font-family: 'Times New Roman', Times, serif; font-size: 18px; color: #333333;">
        <p>Halo Admin,</p>
        <p>Sistem telah berhasil menjalankan perhitungan dan perangkingan SAW secara otomatis untuk periode <b>{period_name}</b>.</p>
        <p>Silakan login ke sistem untuk melihat hasil selengkapnya.</p>
        <br>
        <p>Terima kasih.</p>
        <br>
        <p><i>Sistem Pengawasan Mahasiswa KIP-K (Notifikasi Otomatis)</i></p>
    </body>
    </html>
    """
    
    # --- MODIFIKASI: Kirim email sebagai 'html' ---
    msg = MIMEText(body, 'html')
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