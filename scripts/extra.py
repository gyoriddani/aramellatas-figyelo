"""Extra independent official feeds. Unavailable feeds fail visibly; no synthetic zeroes."""
from __future__ import annotations
import datetime as dt
import email.utils
import json
import os
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
from urllib.request import Request, urlopen

UTC=dt.timezone.utc

def now():return dt.datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00','Z')
def request(url,headers=None,max_bytes=1500000):
    hdr={'User-Agent':'EllatasbiztonsagFigyelo/3.0 (source monitoring; contact via GitHub repo)','Accept':'application/json,application/xml,text/xml,application/rss+xml'}
    hdr.update(headers or {})
    with urlopen(Request(url,headers=hdr),timeout=15) as r:
        if r.status!=200:raise RuntimeError(f'HTTP {r.status}')
        return r.read(max_bytes+1)[:max_bytes]

def tag(el,name):
    for ch in el:
        if ch.tag.split('}')[-1].lower()==name.lower():return (ch.text or '').strip()
    return ''

def rss_items(raw,source,limit=15):
    root=ET.fromstring(raw);items=[]
    for el in root.iter():
        if el.tag.split('}')[-1] not in ('item','entry'):continue
        title=tag(el,'title');link=tag(el,'link');date=tag(el,'pubDate') or tag(el,'updated') or tag(el,'published')
        if not link:
            for ch in el:
                if ch.tag.split('}')[-1]=='link':link=ch.attrib.get('href','');break
        if not title or not link.startswith('https://'):continue
        stamp=None
        try:stamp=email.utils.parsedate_to_datetime(date)
        except (TypeError,ValueError):
            try:stamp=dt.datetime.fromisoformat(date.replace('Z','+00:00'))
            except ValueError:pass
        if stamp and stamp.tzinfo is None:stamp=stamp.replace(tzinfo=UTC)
        items.append({'title':title[:220],'url':link,'published_at':stamp.isoformat() if stamp else None,'source':source})
        if len(items)>=limit:break
    return items

def eu_news():
    urls=[('Európai Bizottság','https://commission.europa.eu/node/2/rss_en'),
          ('GDACS','https://www.gdacs.org/xml/rss.xml')]
    allitems=[];ok=[];errors=[]
    for name,url in urls:
        try:
            parsed=rss_items(request(url),name)
            if not parsed:raise RuntimeError('No RSS/Atom items')
            allitems+=parsed;ok.append(name)
        except Exception as ex:errors.append(name+': '+str(ex)[:110])
    if not ok:raise RuntimeError('; '.join(errors))
    return {'updated_at':now(),'items':allitems[:30],'sources_ok':ok,'partial_errors':errors,
            'note':'Hivatalos hírek, nem riasztások; automatikusan nem kapnak kockázati pontot.'}

def gie_storage():
    key=os.getenv('GIE_API_KEY','').strip()
    if not key: raise RuntimeError('GIE_API_KEY GitHub Secret nincs megadva (opcionális)')
    d=json.loads(request('https://agsi.gie.eu/api?'+urlencode({'country':'HU','size':2}),headers={'x-key':key}))
    rows=d.get('data') if isinstance(d,dict) else None
    if not isinstance(rows,list) or not rows:raise ValueError('AGSI HU data missing')
    out=[]
    for r in rows[:2]:
        try:out.append({'gas_day':r.get('gasDayStart') or r.get('gasDay'),'full_pct':float(r['full'])})
        except (ValueError,TypeError,KeyError):continue
    if not out: raise ValueError('AGSI storage percent missing')
    return {'updated_at':now(),'hu':out,'source':'Gas Infrastructure Europe AGSI+',
            'note':'A tárolói töltöttség nem 24 órás gázellátási zavar valószínűsége.'}

def entsoe_hu_load():
    # Optional token-based, actual day-ahead demand forecast. Demand alone not adequacy.
    key=os.getenv('ENTSOE_API_TOKEN','').strip()
    if not key:raise RuntimeError('ENTSOE_API_TOKEN GitHub Secret nincs megadva (opcionális)')
    today=dt.datetime.now(UTC)
    start=(today-dt.timedelta(hours=3)).strftime('%Y%m%d%H%M')
    end=(today+dt.timedelta(hours=48)).strftime('%Y%m%d%H%M')
    url='https://web-api.tp.entsoe.eu/api?'+urlencode({'securityToken':key,'documentType':'A65','processType':'A01',
          'outBiddingZone_Domain':'10YHU-MAVIR----U','periodStart':start,'periodEnd':end})
    raw=request(url,max_bytes=2000000)
    root=ET.fromstring(raw)
    # Extract quantities explicitly only when TimeSeries appears; resolution may vary.
    nsless=lambda e:e.tag.split('}')[-1]
    timeseries=[e for e in root.iter() if nsless(e)=='TimeSeries']
    if not timeseries:raise ValueError('ENTSO-E API response has no day-ahead TimeSeries')
    vals=[]
    for series in timeseries:
        for pt in series.iter():
            if nsless(pt)!='Point':continue
            q=next((x.text for x in pt if nsless(x)=='quantity'),None)
            try:vals.append(float(q))
            except (TypeError,ValueError):continue
    if not vals:raise ValueError('No load forecast quantities')
    return {'updated_at':now(),'min_mw':round(min(vals)), 'max_mw':round(max(vals)), 'period_start_utc':start,
            'period_end_utc':end,'source':'ENTSO-E Transparency A65 A01',
            'note':'Előrejelzett terhelés; nem azonos a rendelkezésre álló kapacitással vagy hiánykockázattal.'}
