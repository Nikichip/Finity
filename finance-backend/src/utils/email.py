import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_reset_email(to_email: str, code: str, name: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Finity — Your password reset code"
    msg["From"] = EMAIL_USER
    msg["To"] = to_email

    html = f"""
    <div style="font-family:sans-serif;max-width:420px;margin:auto;padding:2rem;background:#10101a;color:#eeeef5;border-radius:12px;">
      <h2 style="color:#6c63ff;margin-bottom:0.5rem;">Finity</h2>
      <p style="color:#8888a8;margin-bottom:1.5rem;">Personal Finance Tracker</p>
      <p>Hi {name},</p>
      <p>Use the code below to reset your password. It expires in <b>10 minutes</b>.</p>
      <div style="text-align:center;margin:2rem 0;">
        <span style="font-size:2.2rem;font-weight:800;letter-spacing:8px;color:#6c63ff;background:#1e1e2e;padding:1rem 2rem;border-radius:10px;">{code}</span>
      </div>
      <p style="color:#8888a8;font-size:0.85rem;">If you didn't request this, you can safely ignore this email.</p>
    </div>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())