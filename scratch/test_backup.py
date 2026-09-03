import smtplib
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "erosrohantorres@gmail.com"
SENDER_PASSWORD = "cfrdfizrjjnzsdwa"
RECIPIENT_EMAIL = "erosrohantorres@gmail.com"

def build_html_template(title, content_html, color_accent="#00ff66"):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                background-color: #0b0f10;
                color: #cfe8d6;
                font-family: 'Segoe UI', Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #14232d;
                border: 1px solid #1e3640;
                border-radius: 8px;
                overflow: hidden;
            }}
            .header {{
                background-color: #071018;
                border-bottom: 2px solid {color_accent};
                padding: 20px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 20px;
                color: #ffffff;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
            .content {{
                padding: 25px;
                font-size: 14px;
                line-height: 1.6;
            }}
            .footer {{
                background-color: #071018;
                border-top: 1px solid #1e3640;
                padding: 15px;
                text-align: center;
                font-size: 11px;
                color: #8a9fa0;
            }}
            .highlight {{
                color: {color_accent};
                font-weight: bold;
            }}
            .button {{
                display: inline-block;
                padding: 10px 20px;
                margin-top: 15px;
                background-color: {color_accent};
                color: #000000;
                text-decoration: none;
                font-weight: bold;
                border-radius: 4px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{title}</h1>
            </div>
            <div class="content">
                {content_html}
            </div>
            <div class="footer">
                VERS - Critical Infrastructure Monitoring System &copy; 2026<br>
                Barangay Bagumbayan, Taguig City, Philippines
            </div>
        </div>
    </body>
    </html>
    """

print("Running synchronous backup email test...")
try:
    msg = MIMEMultipart("mixed")
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = f"[VERS BACKUP TEST] System Code Backup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Create alternative body part for text/html content
    body_part = MIMEMultipart("alternative")
    body_text = "Attached is the automated system code backup containing the current active Python scripts for the VERS Emergency Alert System."
    
    color_accent = "#00bcd4"
    content_html = f"""
    <p>An automated system code backup has been compiled for the VERS Emergency Alert System.</p>
    <p>The current active scripts are attached below:</p>
    <ul style="color: #cfe8d6; margin: 15px 0; padding-left: 20px;">
        <li><span style="font-family: monospace; color: {color_accent};">vers_system.py</span> (Web Server & Dashboard)</li>
        <li><span style="font-family: monospace; color: {color_accent};">vers_simulator.py</span> (Node Simulator)</li>
    </ul>
    <p>These files can be used to redeploy the environment in case of server failure.</p>
    """
    body_html = build_html_template(
        title="VERS - SYSTEM CODE BACKUP",
        content_html=content_html,
        color_accent=color_accent
    )
    
    body_part.attach(MIMEText(body_text, 'plain'))
    body_part.attach(MIMEText(body_html, 'html'))
    msg.attach(body_part)
    
    # Attach files
    files_to_backup = ["vers_system.py", "vers_simulator.py"]
    for fname in files_to_backup:
        if os.path.exists(fname):
            with open(fname, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={fname}",
                )
                msg.attach(part)
                print(f"Attached file: {fname}")
        else:
            print(f"File not found: {fname}")
                
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
    server.close()
    print("Success! Backup email sent.")
except Exception as e:
    print(f"Error: {e}")
