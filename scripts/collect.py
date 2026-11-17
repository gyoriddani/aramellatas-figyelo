#!/usr/bin/env python3
"""Daily public-signal collection. No outage probability or causal claim is inferred.
Run `python scripts/collect.py`. Network failures stay visible as unavailable.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from extra import eu_news, gie_storage, entsoe_hu_load
from grid import europe_grid
from cap import official_cap

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'data' / 'latest.json'
UTC = dt.timezone.utc
EWS_URL = 'https://pub-49bb6a6f314c47be9b481c25e5f6ca9e.r2.dev/dashboard.json'
# Country set intentionally explicit: relevant neighbours, interconnected markets, large EU markets.
COUNTRIES = [
    ('HU','Magyarország',47.9561,21.7187,'hungary','HU'),
    ('AT','Ausztria',48.2082,16.3738,'austria','AT'),
    ('SK','Szlovákia',48.1486,17.1077,'slovakia','SK'),
    ('RO','Románia',44.4268,26.1025,'romania','RO'),
    ('CZ','Csehország',50.0755,14.4378,'czechia','CZ'),
    ('PL','Lengyelország',52.2297,21.0122,'poland','PL'),
    ('DE','Németország',52.5200,13.4050,'germany','DE-LU'),
    ('FR','Franciaország',48.8566,2.3522,'france','FR'),
    ('HR','Horvátország',45.8150,15.9819,'croatia','HR'),
    ('SI','Szlovénia',46.0569,14.5058,'slovenia','SI'),
    ('UA','Ukrajna',50.4501,30.5234,'ukraine',None),
]

# Meteoalarm hivatalos Atom-hírfolyamok (a forrás saját országlistája szerint).
ALERT_COUNTRIES = [
 ('HU','Magyarország','hungary'),('AT','Ausztria','austria'),('SK','Szlovákia','slovakia'),
 ('CZ','Csehország','czechia'),('RO','Románia','romania'),('PL','Lengyelország','poland'),
 ('DE','Németország','germany'),('FR','Franciaország','france'),('HR','Horvátország','croatia'),
 ('SI','Szlovénia','slovenia'),('UA','Ukrajna','ukraine'),('IT','Olaszország','italy'),
 ('ES','Spanyolország','spain'),('GB','Egyesült Királyság','united-kingdom'),
 ('BE','Belgium','belgium'),('NL','Hollandia','netherlands'),('DK','Dánia','denmark'),
 ('SE','Svédország','sweden'),('NO','Norvégia','norway'),('CH','Svájc','switzerland'),
 ('FI','Finnország','finland'),('BG','Bulgária','bulgaria'),('GR','Görögország','greece'),
 ('PT','Portugália','portugal'),('IE','Írország','ireland'),('EE','Észtország','estonia'),
 ('LV','Lettország','latvia'),('LT','Litvánia','lithuania')
]

def now(): return dt.datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00','Z')
def iso_epoch(ts):return dt.datetime.fromtimestamp(float(ts),UTC).isoformat(timespec='seconds').replace('+00:00','Z')
def get_bytes(url, timeout=16):
    req=Request(url,headers={'User-Agent':'HU-ellatasbiztonsag-figyelo/2.0 (public research)','Accept':'application/json, application/atom+xml, application/xml, */*'})
    with urlopen(req,timeout=timeout) as res:
        if res.status!=200: raise RuntimeError('HTTP '+str(res.status))
        raw=res.read(2500000)
        if len(raw)>2000000:raise ValueError('Oversized response')
        return raw

def fetch(url,timeout=16):return json.loads(get_bytes(url,timeout).decode('utf-8-sig'))
def weather():
    q={'latitude':47.9561,'longitude':21.7187,'hourly':'temperature_2m,wind_gusts_10m,precipitation_probability,precipitation,snowfall','timezone':'Europe/Budapest','forecast_days':7}
    d=fetch('https://api.open-meteo.com/v1/forecast?'+urlencode(q));h=d['hourly']
    required=['time','temperature_2m','wind_gusts_10m','precipitation_probability','precipitation','snowfall']
    if any(k not in h for k in required):raise ValueError('Weather fields missing')
    return {'updated_at':now(),'hours':[{'time':str(t),'temperature_c':h['temperature_2m'][i],'gust_kmh':h['wind_gusts_10m'][i], 'rain_probability_pct':h['precipitation_probability'][i],'precip_mm':h['precipitation'][i],'snow_cm':h['snowfall'][i]} for i,t in enumerate(h['time'])]}

def electricity():
    today=dt.datetime.now(UTC).date(); q={'bzn':'HU','start':(today-dt.timedelta(days=1)).isoformat(),'end':(today+dt.timedelta(days=2)).isoformat()}
    d=fetch('https://api.energy-charts.info/price?'+urlencode(q));a=d.get('unix_seconds',[]);b=d.get('price',[])
    prices=[{'time':iso_epoch(t),'eur_mwh':float(p)} for t,p in zip(a,b) if p is not None]
    if not prices:raise ValueError('No HU spot prices')
    return {'updated_at':now(),'prices':prices[-160:]}

def space_weather():
    d=fetch('https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json')
    if not isinstance(d,list) or len(d)<2:raise ValueError('No NOAA rows')
    h=[str(x).lower() for x in d[0]];ti=h.index('time_tag') if 'time_tag' in h else 0
    ki=next((i for i,s in enumerate(h) if s in ('kp','kp_index','kp value') or s.startswith('kp ')),1)
    rows=[]
    for row in d[1:]:
        try:
            tm=str(row[ti]).replace(' ','T')
            if not tm.endswith('Z') and '+' not in tm:tm+='Z'
            rows.append({'time':tm,'kp':float(row[ki])})
        except (ValueError,TypeError,IndexError):pass
    if not rows:raise ValueError('No numeric NOAA values')
    return {'updated_at':now(),'kp':rows[-120:]}

def european_prices():
    today=dt.datetime.now(UTC).date()
    start=(today-dt.timedelta(days=1)).isoformat();end=(today+dt.timedelta(days=2)).isoformat()
    rows=[]; failed=[]
    def one(entry):
        code,name,_,_,__,zone=entry
        if not zone:return None
        d=fetch('https://api.energy-charts.info/price?'+urlencode({'bzn':zone,'start':start,'end':end}),timeout=14)
        vals=[]
        for ts,p in zip(d.get('unix_seconds',[]),d.get('price',[])):
            if p is None:continue
            try: vals.append({'time':iso_epoch(ts),'price':round(float(p),2)})
            except (ValueError,TypeError,OverflowError):continue
        if not vals:raise ValueError('No prices for '+zone)
        # Mean of available hours only. Do not imply identical coverage across markets.
        return {'code':code,'name':name,'zone':zone,'recent_eur_mwh':vals[-1]['price'],'latest_time':vals[-1]['time'],'mean_eur_mwh':round(sum(p['price'] for p in vals)/len(vals),1),'sample_count':len(vals)}
    with ThreadPoolExecutor(max_workers=6) as pool:
        f={pool.submit(one,x):x[0] for x in COUNTRIES if x[-1]}
        for fut in as_completed(f):
            try: rows.append(fut.result())
            except Exception as ex:failed.append(f[fut]+': '+str(ex)[:65])
    if not rows:raise ValueError('No European market data')
    rows.sort(key=lambda x:x['code'])
    return {'updated_at':now(),'countries':rows,'partial_errors':failed, 'metric':'Spot market price context, not shortage evidence'}

def europe_weather():
    # One request for each listed city, not an entire country's weather exposure.
    args={'latitude':','.join(str(x[2]) for x in COUNTRIES),'longitude':','.join(str(x[3]) for x in COUNTRIES), 'hourly':'wind_gusts_10m,temperature_2m,precipitation,snowfall','forecast_days':4,'timezone':'UTC'}
    data=fetch('https://api.open-meteo.com/v1/forecast?'+urlencode(args),timeout=22)
    if not isinstance(data,list) or len(data)!=len(COUNTRIES):raise ValueError('Multi-location forecast missing')
    rows=[]
    floor=dt.datetime.now(UTC)
    until=floor+dt.timedelta(hours=72)
    for entry,d in zip(COUNTRIES,data):
        code,name,*_=entry; h=d.get('hourly',{}); times=h.get('time',[])
        chosen=[]
        for i,t in enumerate(times):
            try:
                stamp=dt.datetime.fromisoformat(str(t)).replace(tzinfo=UTC)
                if not floor<=stamp<=until:continue
                chosen.append({'time':stamp.isoformat().replace('+00:00','Z'),
                   'gust_kmh':h['wind_gusts_10m'][i], 'temperature_c':h['temperature_2m'][i],
                   'precip_mm':h['precipitation'][i], 'snow_cm':h['snowfall'][i]})
            except (ValueError,KeyError,IndexError,TypeError):continue
        def rn(r):
            gust=float(r['gust_kmh'] or 0); rain=float(r['precip_mm'] or 0); snow=float(r['snow_cm'] or 0)
            return max(0,min(100, round(max(0,(gust-35)*1.25,snow*15,max(0,rain-4)*4))))
        if chosen:
            peak=max(chosen,key=rn)
            rows.append({'code':code,'name':name,'peak_time':peak['time'],'gust_kmh':peak['gust_kmh'],'rain_mm':peak['precip_mm'],'snow_cm':peak['snow_cm'],'peak_index':rn(peak)})
    if not rows:raise ValueError('No EU forecast hours')
    return {'updated_at':now(),'countries':rows,'scope_note':'Representative city per country, not entire national grid'}

def parse_date(value):
    if not value:return None
    try:
        v=value.strip().replace('Z','+00:00');d=dt.datetime.fromisoformat(v)
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    except ValueError:return None

def meteoalarm():
    # Official country Atom warnings feeds. We include only recently updated entries;
    # a feed entry alone does not prove warning is currently active.
    codes={code:(name,slug) for code,name,slug in ALERT_COUNTRIES}
    def tag(el,needle):
        for child in el:
            if child.tag.rsplit('}',1)[-1]==needle:return (child.text or '').strip()
        return ''
    def one(entry):
        code,name,slug=entry
        raw=get_bytes('https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-'+slug,timeout=17)
        root=ET.fromstring(raw)
        entries=[]; now_dt=dt.datetime.now(UTC)
        for e in root.iter():
            if e.tag.rsplit('}',1)[-1]!='entry':continue
            title=tag(e,'title'); published=tag(e,'updated') or tag(e,'published'); pt=parse_date(published)
            if not title or not pt or (now_dt-pt).total_seconds()>3*86400:continue
            if pt > now_dt+dt.timedelta(hours=12):continue
            href='https://www.meteoalarm.org/'
            for child in e:
                if child.tag.rsplit('}',1)[-1]=='link' and child.attrib.get('href','').startswith('https://'):
                    href=child.attrib['href'];break
            entries.append({'country':code,'name':name,'title':title[:170],'published_at':pt.isoformat().replace('+00:00','Z'),'url':href})
        return code,entries
    out=[];ok=[];errs=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        f={pool.submit(one,(code,name,slug)):code for code,(name,slug) in codes.items()}
        for fut in as_completed(f):
            try: code,entries=fut.result();ok.append(code);out.extend(entries[:12])
            except Exception as ex:errs.append(f[fut]+': '+str(ex)[:50])
    if not ok:raise ValueError('No official Atom feeds accessible')
    out.sort(key=lambda x:x['published_at'],reverse=True)
    return {'updated_at':now(),'countries_checked':sorted(ok),'recent_entries':out[:65],'partial_errors':errs,
            'note':'Recently published Atom entries, not verified active alerts or blackouts'}

def ews():
    # Public dashboard snapshot URL published by EWS project's own README.
    d=fetch(EWS_URL,timeout=20)
    if not isinstance(d,dict):raise ValueError('EWS response not JSON object')
    # Conservative key parsing: preserve source values without converting them to outage risk.
    sources=[d]+[d[k] for k in ('summary','current','live','status','snapshot','signal') if isinstance(d.get(k),dict)]
    level=None;count=None;asof=None
    for row in sources:
        for k in ('emergencyLevel','emergency_level','currentEmergencyLevel','level'):
            v=row.get(k)
            if isinstance(v,(int,float)) and not isinstance(v,bool) and 1<=v<=5:
                level=float(v);break
        if level is not None:break
    for row in sources:
        for k in ('airborneCount','airborne_count','currentCount','count'):
            v=row.get(k)
            if isinstance(v,(int,float)) and not isinstance(v,bool) and 0<=v<=100000:
                count=int(v);break
        if count is not None:break
    for row in sources:
        for k in ('updatedAt','updated_at','timestamp','generated_at'):
            v=row.get(k)
            if isinstance(v,str) and parse_date(v):asof=v;break
        if asof:break
    return {'updated_at':now(),'level':level,'airborne_count':count,'source_timestamp':asof,'data_available':True,
            'note':'Speculative business-jet anomaly signal. Does not establish a causal link to an emergency.','url':'https://ews.kylemcdonald.net/'}

def main():
    previous={}
    if TARGET.exists():
        try: previous=json.loads(TARGET.read_text(encoding='utf8'))
        except (ValueError,OSError):pass
    out={'generated_at':now(),'location':'Nyíregyháza, Magyarország','timezone':'Europe/Budapest','feeds':previous.get('feeds',{}),'errors':{}}
    # Avoid silently preserving stale data as fresh: each feed has its own updated_at.
    successes=set()
    jobs=[('weather',weather),('electricity',electricity),('space_weather',space_weather),
          ('european_prices',european_prices),('europe_weather',europe_weather),
          ('meteoalarm',meteoalarm),('ews',ews),('official_news',eu_news),('gie_storage',gie_storage),('entsoe_hu_load',entsoe_hu_load),('grid_context',europe_grid),('cap_warnings',official_cap)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(fn):name for name,fn in jobs}
        for fut in as_completed(futures):
            name=futures[fut]
            try:out['feeds'][name]=fut.result();successes.add(name);print(name,'OK')
            except Exception as ex:out['errors'][name]=str(ex)[:190];print(name,'NINCS ADAT',str(ex)[:190])
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    TARGET.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if not any(x in successes for x in ('weather','electricity','space_weather','european_prices','europe_weather')):
        raise SystemExit('No primary observation feed available')

if __name__=='__main__':main()
