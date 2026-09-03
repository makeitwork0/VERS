import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "erosrohantorres@gmail.com"
SENDER_PASSWORD = "cfrdfizrjjnzsdwa"
RECIPIENT_EMAIL = "erosrohantorres@gmail.com"

print("Testing Gmail SMTP connection...")
try:
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = "[VERS TEST] Credentials Check"
    msg.attach(MIMEText("This is a direct synchronous test of your Gmail SMTP app password credentials. If you receive this, the system is fully operational and email alerts are working!", 'plain'))
    
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
    server.close()
    print("Success! Email sent successfully.")
except Exception as e:
    print(f"Error: {e}")
