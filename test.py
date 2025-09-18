import smtplib
from instance.api_key import DEL_EMAIL, DEL_PASSWORD
EMAIL = DEL_EMAIL
APP_PASSWORD = DEL_PASSWORD 

try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.login(EMAIL, APP_PASSWORD)
    print("✅ Connection successful using TLS on port 587")
    server.quit()
except Exception as e:
    print("❌ TLS connection failed:", e)


try:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL, APP_PASSWORD)
    print("✅ Connection successful using SSL on port 465")
    server.quit()
except Exception as e:
    print("❌ SSL connection failed:", e)