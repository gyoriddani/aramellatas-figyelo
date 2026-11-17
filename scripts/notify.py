#!/usr/bin/env python3
"""SMTP alert: real confirmed notices / uncalibrated indices, plus degraded data quality.
Never claims probability or success if no SMTP credentials.
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
THRESHOLD=50

def parse(t):
    try:
        x=dt.datetime.fromisoformat(str(t).replace('Z','+00:00'))
        return x if x.tzinfo else x.replace(tzinfo=UTC)
    except (ValueError,TypeError):return None

def eligible(assessment,state,now):
    chosen=[];sent=state.get('sent',{})
    for c in assessment.get('categories',[]):
        score=c.get('score')
        if c.get('status') not in ('estimated_index','verified_notice','official_cap') or not isinstance(score,(int,float)) or score<THRESHOLD:continue
        prev=sent.get(c['key'],{});old=parse(prev.get('at'))
        if old and now-old<dt.timedelta(hours=24) and score<=prev.get('score',0):continue
        chosen.append(c)
    return chosen

def health_problem(assessment,state,now):
    health=assessment.get('health') or {}
    if not health.get('degraded'):return False
    old=parse((state.get('health') or {}).get('at'))
    missing_count=len(health.get('important_missing',[]))
    prev_count=(state.get('health') or {}).get('count',0)
    return old is None or now-old>=dt.timedelta(hours=24) or missing_count>prev_count

def compose(chosen,assessment,now,recipient,health_alert=False):
    msg=EmailMessage()
    msg['Subject']='[ELLÁTÁSBIZTONSÁG] '+ ('Jelzés és adatminőségi hiba' if health_alert and chosen else 'Adatgyűjtési hiba' if health_alert else '24 órás kockázati jelzés')
    msg['To']=recipient
    lines=['ELLÁTÁSBIZTONSÁGI FIGYELŐ — NYÍREGYHÁZA',
           'Ellenőrzés: '+now.astimezone(ZoneInfo('Europe/Budapest')).strftime('%Y-%m-%d %H:%M')+' (magyar idő)',
           '', 'FIGYELEM: AZ 50/100 KOCKÁZATI PONT NEM 50% ESEMÉNYVALÓSZÍNŰSÉG.',
           'Az index nem kalibrált, nem alkalmas önálló vészhelyzeti döntésre.','']
    if health_alert:
        h=assessment.get('health',{})
        lines+=['ADATGYŰJTÉSI HIBA',f"Elsődleges források: {h.get('important_fresh','?')}/{h.get('important_total','?')} friss.",
                'Hiányzó vagy elavult: '+', '.join(h.get('important_missing',[])),
                'A kiesett források NEM jelentik azt, hogy nincs veszély.','']
    for c in chosen:
        lines += [f"{c['name']}: {c['score']}/100 ({c['status']})",
                  'Időablak / csúcs: '+str(c.get('peak_time') or 'nincs pontos idő'),
                  'Érintett terület: '+str(c.get('scope') or 'nincs megadva')]
        for e in (c.get('evidence') or [])[:3]:
            lines += [f" - {e.get('source','Forrás')}: {e.get('detail','')}",f"   {e.get('url','')}"]
        lines+=['']
    o=assessment.get('overall',{})
    lines += [f"Lefedettség (24h): {o.get('coverage','?')}/{o.get('total_categories','?')} kategória.",
              'A nem becsülhető kategóriák nem jelentenek nullakockázatot.',
              'Elsőként a szolgáltató és a hatóságok aktuális közleményeit ellenőrizd.',
              'https://www.opustitasz.hu/kapcsolat/hibabejelentes/hibabejelentes',
              'https://www.katasztrofavedelem.hu/37/vesz']
    msg.set_content('\n'.join(lines));return msg

def main():
    data=json.loads(DATA.read_text(encoding='utf8'));a=data.get('assessment',{})
    state=json.loads(STATE.read_text(encoding='utf8')) if STATE.exists() else {'sent':{}}
    now=dt.datetime.now(UTC)
    created=parse(a.get('generated_at'))
    if not created or abs((now-created).total_seconds())>7200:
        raise RuntimeError('Nem friss az értékelés; riasztás nem küldhető.')
    chosen=eligible(a,state,now)
    bad=health_problem(a,state,now)
    if not chosen and not bad:print('Nincs új küszöbátlépés vagy jelentős adatgyűjtési hiba.');return
    username=os.getenv('SMTP_USER','').strip();password=os.getenv('SMTP_APP_PASSWORD','').strip();recipient=os.getenv('ALERT_TO','').strip()
    if not all((username,password,recipient)):
        raise RuntimeError('Riasztás lenne, de SMTP_USER, SMTP_APP_PASSWORD vagy ALERT_TO hiányzik. E-mail nem ment ki.')
    msg=compose(chosen,a,now,recipient,bad);msg['From']=username
    with smtplib.SMTP_SSL('smtp.gmail.com',465,context=ssl.create_default_context(),timeout=30) as server:
        server.login(username,password);server.send_message(msg)
    state.setdefault('sent',{})
    for c in chosen:state['sent'][c['key']]={'at':now.isoformat(),'score':c['score']}
    if bad:state['health']={'at':now.isoformat(),'count':len(a['health']['important_missing'])}
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Értesítés sikeresen elküldve; kategóriák:',len(chosen),'adatgyűjtési hiba:',bad)

if __name__=='__main__':main()
