#!/usr/bin/env python3
"""Send a separate execution failure notice, if workflow did not complete."""
import os
import smtplib
import ssl
from email.message import EmailMessage

status=os.getenv('MONITOR_JOB_STATUS','')
if status!='failure':
    print('A futás nem hibás; nincs hibaértesítés.')
    raise SystemExit(0)
username=os.getenv('SMTP_USER','').strip()
password=os.getenv('SMTP_APP_PASSWORD','').strip()
recipient=os.getenv('ALERT_TO','').strip()
if not (username and password and recipient):
    print('A futás hibás, de a három SMTP secret nincs teljesen beállítva.')
    raise SystemExit(1)
msg=EmailMessage()
msg['From']=username
msg['To']=recipient
msg['Subject']='[ELLÁTÁSBIZTONSÁG] GitHub Actions futási hiba'
msg.set_content('Az adatgyűjtő munkafolyamat hibával végződött.\nEz nem jelent vészhelyzetet, de a figyelő adatai elavulhatnak.\n'+os.getenv('RUN_LINK','')+'\n')
with smtplib.SMTP_SSL('smtp.gmail.com',465,context=ssl.create_default_context(),timeout=25) as server:
    server.login(username,password)
    server.send_message(msg)
print('Futási hibaértesítés elküldve.')
