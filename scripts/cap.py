"""Strict CAP warning verification from official Meteoalarm Atom feeds.
A single region-wide warning never establishes a countrywide power failure.
Only Actual, non-cancelled, time-bounded records are included.
"""
from __future__ import annotations
import datetime as dt
import xml.etree.ElementTree as ET
from urllib.request import Request,urlopen
UTC=dt.timezone.utc
COUNTRIES={'HU':'hungary','SK':'slovakia','RO':'romania','AT':'austria'}
URL_ROOT='https://feeds.meteoalarm.org/'

def local_tag(el):return el.tag.rsplit('}',1)[-1].lower()
def first(el,name):
    if el is None:return ''
    for c in el:
        if local_tag(c)==name:return (c.text or '').strip()
    return ''
def timestamp(v):
    if not v:return None
    try:
        d=dt.datetime.fromisoformat(v.replace('Z','+00:00'))
        return d.astimezone(UTC) if d.tzinfo else d.replace(tzinfo=UTC)
    except (ValueError,TypeError):return None

def read(url):
    if not url.startswith(URL_ROOT):raise ValueError('Nem Meteoalarm URL')
    req=Request(url,headers={'User-Agent':'SupplyRiskMonitor/4.0','Accept':'application/xml,application/atom+xml,text/xml'})
    with urlopen(req,timeout=14) as response:
        if response.status!=200:raise ValueError('HTTP '+str(response.status))
        content=response.read(750001)
        if len(content)>750000:raise ValueError('Too big XML')
        return content

def parse_cap(raw,country,link):
    root=ET.fromstring(raw)
    if local_tag(root)!='alert':return []
    if first(root,'status').lower()!='actual':return []
    if first(root,'msgtype').lower() in ('cancel','ack','error'):return []
    result=[]
    for info in root:
        if local_tag(info)!='info':continue
        severity=first(info,'severity').lower()
        if severity not in ('minor','moderate','severe','extreme'):continue
        expires=timestamp(first(info,'expires'))
        begin=timestamp(first(info,'onset')) or timestamp(first(info,'effective'))
        if not begin or not expires or begin>=expires:continue
        scope=[]
        for area in info:
            if local_tag(area)=='area':
                desc=first(area,'areadesc')
                if desc:scope.append(desc)
        result.append({'country':country,'title':(first(info,'headline') or first(info,'event'))[:200],
                       'event':first(info,'event')[:100],'severity':severity,
                       'onset':begin.isoformat(),'expires':expires.isoformat(),
                       'area':'; '.join(scope)[:260] or 'Terület nincs megadva',
                       'url':link,'source':'Meteoalarm / nemzeti meteorológiai szolgálat'})
    return result

def official_cap():
    now=dt.datetime.now(UTC)
    alerts=[];ok=[];fail=[]
    for country,slug in COUNTRIES.items():
        try:
            raw=read(URL_ROOT+'feeds/meteoalarm-legacy-atom-'+slug)
            root=ET.fromstring(raw)
            entries=[e for e in root.iter() if local_tag(e)=='entry']
            extracted=[]
            # Follow at most three recently published CAP messages per country.
            for entry in entries[:6]:
                published=timestamp(first(entry,'updated') or first(entry,'published'))
                if published and now-published>dt.timedelta(days=4):continue
                links=[e.attrib.get('href','') for e in entry if local_tag(e)=='link']
                caplinks=[u for u in links if u.startswith(URL_ROOT) and u!='https://feeds.meteoalarm.org/']
                caplinks.sort(key=lambda u: (0 if ('/api/' in u or u.endswith('.xml')) else 1, len(u)))
                for url in caplinks[:2]:
                    try:
                        found=parse_cap(read(url),country,url)
                        extracted.extend(x for x in found if timestamp(x['expires'])>now and timestamp(x['onset'])<=now+dt.timedelta(hours=72))
                    except Exception:pass
                if len(extracted)>=10:break
            alerts+=extracted[:10];ok.append(country)
        except Exception as e:fail.append(country+': '+str(e)[:100])
    if not ok:raise RuntimeError('CAP Atom feeds not reachable: '+'; '.join(fail))
    return {'updated_at':now.isoformat(),'countries_checked':ok,'alerts':alerts,
            'partial_errors':fail,'method':'Strict CAP, actual status, valid time bounds; local area not guaranteed.'}
