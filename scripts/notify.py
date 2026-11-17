#!/usr/bin/env python3
"""Send only new/high 24h INDEX warnings with configured Gmail SMTP Secrets.
Without all secrets nothing is sent, and we don't claim to have sent anything.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/latest.json'
STATE=ROOT/'data/alert_state.json'
UTC=dt.timezone.utc

def eligible(assessment, state, now):
    chosen=[]
    sent=state.get('sent',{})
    for c in assessment.get('categories',[]):
        score=c.get('score')
        if c.get('status') not in ('estimated_index','verified_notice') or not isinstance(score,(int,float)) or score<50:continue
        name=c['key'];was=sent.get(name,{})
        try: previous=dt.datetime.fromisoformat(was.get('at',''))
        except (ValueError,TypeError):previous=None
        if previous and previous.tzinfo is None:previous=previous.replace(tzinfo=UTC)
        if previous and now-previous<dt.timedelta(hours=24) and score<=was.get('score',0):continue
        chosen.append(c)
    return chosen

def compose(chosen, asmt, now, recipient):
    msg=EmailMessage();msg['Subject']='[ELLÁTÁSBIZTONSÁG] 24 órás figyelmeztetés – index ≥50/100';msg['To']=recipient
    lines=['24 ÓRÁS ELLÁTÁSBIZTONSÁGI FIGYELMEZTETÉS',f'Értékelés: {now.astimezone(ZoneInfo('Europe/Budapest')).strftime("%Y-%m-%d %H:%M")} (magyar idő)',
           '', 'FIGYELEM: 50/100 KOCKÁZATI INDEX NEM 50% BEKÖVETKEZÉSI VALÓSZÍNŰSÉG.',
           'Az index szabályalapú, nincs történelmi eseményeken kalibrálva.','']
    for c in chosen:
        lines += [f"{c['name']}: {c['score']}/100 ({c['status']})",f"Várható jelzési csúcs / közlemény kezdete: {c.get('peak_time') or 'nincs időpont'}",f"Térség: {c.get('scope') or '—'}"]
        for ev in c.get('evidence',[])[:3]:lines += [f" - {ev.get('source')}: {ev.get('detail')}",f"   {ev.get('url')}"]
        lines.append('')
    lines += [f"Adatlefedettség: {asmt['overall']['coverage']}/{asmt['overall']['total_categories']} kategória.",
              'Hiányzó adatokból nem következtetünk alacsony kockázatra.',
              'Ellenőrizd a szolgáltató és a hatóság hivatalos riasztásait.',
              'https://www.opustitasz.hu/  |  https://www.katasztrofavedelem.hu/  |  https://www.entsoe.eu/']
    msg.set_content('\n'.join(lines));return msg

def main():
    d=json.loads(DATA.read_text(encoding='utf8'));asmt=d.get('assessment',{})
    sent= json.loads(STATE.read_text(encoding='utf8')) if STATE.exists() else {'sent':{}}
    now=dt.datetime.now(UTC)
    if not asmt:raise SystemExit('Nincs friss értékelés; értesítés letiltva.')
    try: created=dt.datetime.fromisoformat(asmt['generated_at'])
    except (KeyError,ValueError):raise SystemExit('Értékelés időbélyeg nélkül; értesítés letiltva.')
    if now-created>dt.timedelta(hours=2):raise SystemExit('Elavult értékelés; értesítés letiltva.')
    chosen=eligible(asmt,sent,now)
    if not chosen:print('Nincs új, 50 pontot elérő jelzés.');return
    username=os.getenv('SMTP_USER','').strip();password=os.getenv('SMTP_APP_PASSWORD','').strip()
    receiver=os.getenv('ALERT_TO','').strip()
    if not all((username,password,receiver)):
        print('Riasztási küszöb teljesült, de SMTP_USER, SMTP_APP_PASSWORD vagy ALERT_TO hiányzik: NEM küldtünk e-mailt.')
        return
    msg=compose(chosen,asmt,now,receiver);msg['From']=username
    with smtplib.SMTP_SSL('smtp.gmail.com',465,context=ssl.create_default_context(),timeout=20) as server:
        server.login(username,password);server.send_message(msg)
    print('E-mail elküldve',len(chosen),'kategóriáról (cím nincs naplózva).')
    sent.setdefault('sent',{})
    for c in chosen:sent['sent'][c['key']]={'at':now.isoformat(),'score':c['score']}
    STATE.write_text(json.dumps(sent,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
