#!/usr/bin/env python3
"""24h monitoring indicators, NOT event probabilities. Standard library only.
A score represents an explicit, non-calibrated alert index. Absent evidence remains null.
"""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'latest.json'
OFFICIAL = ROOT / 'data' / 'official_alerts.json'
UTC = dt.timezone.utc
LOCAL = ZoneInfo('Europe/Budapest')
FRESH_HOURS = 30
THRESHOLD = 50

CATEGORIES = [
 ('local_power','Helyi áramszünet','Időjárási hálózati kitettség, nem áramszünet-valószínűség'),
 ('national_power','Országos blackout','Csak hiteles, területre vonatkozó hivatalos ellátási riasztás esetén'),
 ('eu_power','Európai áramellátási zavar','EU-s kapacitásmegfelelőségi és hivatalos jelzés'),
 ('cyber','Kibertámadás','Csak megerősített hivatalos jelzés; hálózati kiesés nem bizonyít támadást'),
 ('internet','Internet/kommunikáció kiesése','Csak megerősített hivatalos jelzés'),
 ('food','Élelmiszerellátási zavar','Csak megerősített hivatalos jelzés'),
 ('fuel','Üzemanyaghiány','Csak megerősített hivatalos jelzés'),
 ('gas','Gázellátási zavar','Csak megerősített hivatalos jelzés'),
 ('terror','Terrortámadás','Csak megerősített hivatalos figyelmeztetés'),
 ('war','Háborús eszkaláció','Csak megerősített hivatalos figyelmeztetés'),
 ('default','Államcsőd/pénzügyi válság','Nincs rövid távú hiteles százalékos modell'),
 ('extreme_weather','Szélsőséges időjárás','Mért előrejelzési kitettség; nem eseményvalószínűség'),
 ('geomagnetic','Geomágneses vihar','NOAA Kp előrejelzés; nem elektromos hálózat-kiesési esély'),
]
SEVERITY_POINTS = {'information':20, 'warning':55, 'severe':75, 'emergency':95}

def parse_iso(s):
    try:
        t=dt.datetime.fromisoformat(str(s).strip().replace('Z','+00:00'))
        return (t if t.tzinfo else t.replace(tzinfo=UTC)).astimezone(UTC)
    except (ValueError,TypeError):
        return None

def age_ok(feed, now):
    if not isinstance(feed,dict): return False
    stamped=parse_iso(feed.get('updated_at'))
    return stamped is not None and -dt.timedelta(minutes=5) <= now-stamped <= dt.timedelta(hours=FRESH_HOURS)

def num(v):
    try: return float(v) if v is not None else None
    except (TypeError, ValueError, OverflowError): return None

def cap(v):return round(max(0,min(100,v)))

def gust_score(g):
    if g<35:return 0
    if g<50:return (g-35)*1.1
    if g<70:return 17+(g-50)*1.6
    if g<90:return 49+(g-70)*1.55
    return min(100,80+(g-90)*0.8)

def weather_score(h):
    gust=num(h.get('gust_kmh'));mm=num(h.get('precip_mm'));snow=num(h.get('snow_cm'));temp=num(h.get('temperature_c'))
    if gust is None or mm is None or snow is None: return None
    wind=gust_score(gust); snowfall=min(80,max(0,snow)*15)
    rain=min(70,max(0,mm-4)*4)
    frost=min(20,max(0,-15-temp)*2) if temp is not None else 0
    compound=10 if gust>=65 and (snow>.3 or mm>5) else 0
    return cap(max(wind,snowfall,rain,frost)+compound)

def baseline(now):
    return {key:{'key':key,'name':name,'method':method,'score':None,'status':'not_estimated',
                 'peak_time':None,'evidence':[],'scope':'Magyarország / 24 óra',
                 'probability_pct':None,'why_unavailable':'Nincs validált, 24 órás eseményvalószínűségi modell.'}
            for key,name,method in CATEGORIES}

def evaluate(data, official, now=None):
    now=now or dt.datetime.now(UTC)
    end=now+dt.timedelta(hours=24)
    categories=baseline(now)
    feeds=data.get('feeds',{})
    # Weather is a local weather-exposure indicator. Not outage likelihood.
    w=feeds.get('weather')
    if age_ok(w,now) and isinstance(w.get('hours'),list):
        rows=[]
        for h in w['hours']:
            t=parse_iso(h.get('time'))  # local Open-Meteo time is timezone-naive
            if isinstance(h.get('time'),str) and ('+' not in h['time'] and not h['time'].endswith('Z')):
                try:t=dt.datetime.fromisoformat(h['time']).replace(tzinfo=LOCAL).astimezone(UTC)
                except ValueError:t=None
            score=weather_score(h)
            if t and now<=t<=end and score is not None:rows.append((score,t,h))
        if rows:
            s,t,h=max(rows,key=lambda r:r[0])
            evidence={'source':'Open-Meteo','url':'https://open-meteo.com/en/docs',
                'detail':f"Széllökés {h.get('gust_kmh')} km/h, csapadék {h.get('precip_mm')} mm/h, hó {h.get('snow_cm')} cm; 24h csúcs",
                'time':t.isoformat()}
            for key in ('local_power','extreme_weather'):
                c=categories[key];c.update(score=s,peak_time=t.isoformat(),status='estimated_index',evidence=[evidence],why_unavailable=None)
                c['scope']='Nyíregyháza / 24 óra'
    # Space weather: severity of predicted NOAA signal. Not blackout likelihood.
    f=feeds.get('space_weather')
    if age_ok(f,now) and isinstance(f.get('kp'),list):
        kp=[]
        for item in f['kp']:
            t=parse_iso(item.get('time'));v=num(item.get('kp'))
            if t and v is not None and now<=t<=end:kp.append((v,t))
        if kp:
            v,t=max(kp)
            s=0 if v<5 else 40 if v<6 else 55 if v<7 else 70 if v<8 else 90 if v<9 else 100
            c=categories['geomagnetic'];c.update(score=s,peak_time=t.isoformat(),status='estimated_index',why_unavailable=None,
                evidence=[{'source':'NOAA SWPC','url':'https://www.swpc.noaa.gov/','detail':f'Előrejelzett Kp {v:g}', 'time':t.isoformat()}])
    # Operator-maintained, explicitly verified notices from official sources only.
    # No unverified media and no EWS signal ever turn into an emergency score.
    accepted=[];rejected=[]
    for item in official.get('alerts',[]):
        try:
            key=item['category'];severity=item['severity'];url=str(item['url'])
            start=parse_iso(item['start_at']);expiry=parse_iso(item['expires_at'])
            if key not in categories or severity not in SEVERITY_POINTS:continue
            if not url.startswith('https://'):continue
            if start is None or expiry is None or not (start<=end and expiry>now):continue
            # source must be explicitly reviewed/entered by the repository owner
            if item.get('verified') is not True:continue
            s=SEVERITY_POINTS[severity]
            ev={'source':'Hivatalos, kézzel ellenőrzött közlemény', 'url':url,
                'detail':str(item.get('title','Hivatalos figyelmeztetés'))[:240], 'time':start.isoformat()}
            c=categories[key]
            if c['score'] is None or s>c['score']:
                c.update(score=s,status='verified_notice',peak_time=start.isoformat(),evidence=[ev],why_unavailable=None,
                    scope=str(item.get('scope','Hivatalos közlemény'))[:90])
            else:c['evidence'].append(ev)
            accepted.append({'category':key,'severity':severity,'url':url})
        except (KeyError,TypeError):rejected.append(str(item)[:70])
    scored=[x for x in categories.values() if x['score'] is not None]
    high=[x for x in scored if x['score']>=THRESHOLD]
    primary=max(scored,key=lambda c:c['score']) if scored else None
    return {'generated_at':now.isoformat(),'horizon_hours':24,'threshold':THRESHOLD,
        'threshold_unit':'index_points_not_probability',
        'probability_note':'Nem számolunk validált bekövetkezési százalékot. 50/100 pont ≠ 50% eseményesély.',
        'overall':{'score':primary['score'] if primary else None,'category':primary['key'] if primary else None,
            'method':'Legmagasabb elérhető kategóriaindex; hiányzó kategóriák NEM nulla kockázat.',
            'coverage':len(scored),'total_categories':len(categories),'complete':len(scored)==len(categories)},
        'categories':list(categories.values()),'alerts':[x['key'] for x in high],
        'official_notices_accepted':accepted,'official_notices_rejected_count':len(rejected)}

def main():
    data=json.loads(DATA.read_text(encoding='utf8'))
    official=json.loads(OFFICIAL.read_text(encoding='utf8')) if OFFICIAL.exists() else {'alerts':[]}
    evaluation=evaluate(data,official)
    data['assessment']=evaluation
    DATA.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Kategóriák:',evaluation['overall']['coverage'],'/',evaluation['overall']['total_categories'],
          '; riasztási indexek:',evaluation['alerts'])

if __name__=='__main__':main()
