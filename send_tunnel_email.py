import sys
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(tunnel_url):
    try:
        with open('/home/rasp-pi/vers_project/data/settings.json', 'r') as f:
            settings = json.load(f)
        
        smtp_server = settings.get("smtp_server", "smtp.gmail.com")
        smtp_port = int(settings.get("smtp_port", 587))
        sender_email = settings.get("sender_email")
        sender_password = settings.get("sender_password")
        recipient_email = settings.get("recipient_email", sender_email)

        if not sender_email or not sender_password:
            print("Missing sender email or password in settings.json")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🌐 VERS Dashboard Live Cloudflare Access Link"
        msg["From"] = f"VERS System <{sender_email}>"
        msg["To"] = recipient_email

        text = f"""
Hello Operator,

Your VERS (Critical Infrastructure Monitor) dashboard is accessible online via Cloudflare Quick Tunnel:

🔗 Live Dashboard URL: {tunnel_url}

You can click the link above from any device anywhere in the world to view real-time weather warnings, rainfall radar, GDACS cyclones, and system health.

Best regards,
VERS Automated Monitoring System
        """

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #0b0f10; color: #cfe8d6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #071018; border: 1px solid #1e3640; border-radius: 8px; padding: 25px;">
                <h2 style="color: #00ff66; margin-top: 0;">🌐 VERS Dashboard Remote Access</h2>
                <p style="font-size: 15px; color: #8a9fa0;">Your VERS Critical Infrastructure Monitor dashboard has been exposed via Cloudflare Tunnel:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{tunnel_url}" style="background-color: #00ff66; color: #000; padding: 14px 28px; font-weight: bold; text-decoration: none; border-radius: 6px; font-size: 16px; display: inline-block;">🚀 Open VERS Dashboard</a>
                </div>
                <p style="font-size: 13px; color: #8a9fa0; background: #0f1618; padding: 10px; border-radius: 4px; border-left: 3px solid #00bcd4;">
                    <strong>Direct Link:</strong> <a href="{tunnel_url}" style="color: #00bcd4;">{tunnel_url}</a>
                </p>
                <hr style="border: 0; border-top: 1px solid #1e3640; margin: 20px 0;">
                <p style="font-size: 11px; color: #666; text-align: center;">VERS System Automated Cloudflare Service</p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        print(f"Successfully emailed tunnel URL ({tunnel_url}) to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.trycloudflare.com"
    send_email(url)
