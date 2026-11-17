#!/usr/bin/env python3
"""Collect independent public signals for the static Hungarian continuity dashboard.

Run with: python scripts/collect.py
Uses public third-party endpoints; a failed feed stays stale, never becomes zero risk.
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data" / "latest.json"
UTC = dt.timezone.utc

def now():
    return dt.datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00','Z')

def iso_from_epoch(ts):
    return dt.datetime.fromtimestamp(float(ts), UTC).isoformat(timespec='seconds').replace('+00:00','Z')

def fetch(url):
    req = Request(url, headers={"User-Agent": "HU-ellatasbiztonsag-figyelo/1.0 (community research)","Accept": "application/json"})
    with urlopen(req, timeout=22) as res:
        return json.loads(res.read().decode('utf-8'))

def weather():
    args = {"latitude":47.9561,"longitude":21.7187,"hourly":"temperature_2m,wind_gusts_10m,precipitation_probability,precipitation,snowfall","timezone":"Europe/Budapest","forecast_days":7}
    data = fetch('https://api.open-meteo.com/v1/forecast?' + urlencode(args))
    h = data['hourly']
    for required in ('time','temperature_2m','wind_gusts_10m','precipitation_probability','precipitation','snowfall'):
        if required not in h: raise ValueError('Missing weather field: ' + required)
    # Keep local times and report explicit zone; Javascript can format local wall clock consistently.
    return {"updated_at":now(), "hours": [
        {"time":str(t),"temperature_c":h['temperature_2m'][i],"gust_kmh":h['wind_gusts_10m'][i],
         "rain_probability_pct":h['precipitation_probability'][i],"precip_mm":h['precipitation'][i],"snow_cm":h['snowfall'][i]}
        for i,t in enumerate(h['time'])
    ]}

def electricity():
    # Day-ahead market prices are contextual, NOT an electricity outage forecast.
    today = dt.datetime.now(UTC).date()
    args = {'bzn':'HU','start':(today-dt.timedelta(days=1)).isoformat(), 'end':(today+dt.timedelta(days=2)).isoformat()}
    d=fetch('https://api.energy-charts.info/price?' + urlencode(args))
    ts=d.get('unix_seconds',[]); ps=d.get('price',[])
    if not ts or not ps: raise ValueError('No market data')
    vals=[]
    for t,p in zip(ts,ps):
        if p is not None:
            vals.append({'time':iso_from_epoch(t),'eur_mwh':float(p)})
    if not vals:raise ValueError('No valid price records')
    return {'updated_at':now(),'prices':vals[-160:]}

def space_weather():
    d=fetch('https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json')
    if not isinstance(d,list) or len(d)<2:raise ValueError('No Kp forecast rows')
    header=[str(x).lower() for x in d[0]]
    t_idx=header.index('time_tag') if 'time_tag' in header else 0
    kp_idx=next((i for i,s in enumerate(header) if s in ('kp','kp_index','kp value') or s.startswith('kp ')),1)
    rows=[]
    for r in d[1:]:
        try:
            stamp=str(r[t_idx]).replace(' ', 'T')
            if not stamp.endswith('Z') and '+' not in stamp:stamp+='Z'
            rows.append({'time':stamp,'kp':float(r[kp_idx])})
        except (IndexError, TypeError, ValueError):continue
    if not rows:raise ValueError('No numeric Kp forecast')
    return {'updated_at':now(),'kp':rows[-120:]}

def main():
    previous={}
    if TARGET.exists():
        try: previous=json.loads(TARGET.read_text(encoding='utf8'))
        except (ValueError,OSError): pass
    out={'generated_at':now(),'location':'Nyíregyháza, Magyarország', 'timezone':'Europe/Budapest','feeds':previous.get('feeds',{}), 'errors':{}}
    for key,fn in [('weather',weather),('electricity',electricity),('space_weather',space_weather)]:
        try:
            out['feeds'][key]=fn()
            print(key,'OK')
        except Exception as ex:
            out['errors'][key]=str(ex)[:180]
            print(key,'ERROR',str(ex)[:180])
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    TARGET.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'),indent=2)+'\n',encoding='utf8')
    if not out['feeds']:
        raise SystemExit('No data feed available; leaving empty status file')

if __name__=='__main__': main()
