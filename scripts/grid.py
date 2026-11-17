"""European power context via Fraunhofer Energy-Charts v2.

Every successful series is *context*, never an adequacy or outage probability.
API may lack data for a requested country; each gap stays explicit.
"""
from __future__ import annotations
import datetime as dt
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

UTC=dt.timezone.utc
BASE='https://api.energy-charts.info/v2/'

def numeric(v):
    if isinstance(v,bool) or v is None:return None
    try:
        f=float(v)
        return f if -1e10<f<1e10 else None
    except (TypeError,ValueError):return None

def iso(v):
    try:
        if isinstance(v,(int,float)):
            d=dt.datetime.fromtimestamp(v,UTC)
        else:
            d=dt.datetime.fromisoformat(str(v).replace('Z','+00:00'))
            if not d.tzinfo:d=d.replace(tzinfo=UTC)
        return d.astimezone(UTC).isoformat().replace('+00:00','Z')
    except (OverflowError,TypeError,ValueError):return None

def get(url):
    request=Request(url,headers={'User-Agent':'SupplyRiskMonitor/4.0 (personal monitoring)','Accept':'application/json'})
    with urlopen(request,timeout=18) as response:
        if response.status!=200:raise ValueError(f'HTTP {response.status}')
        b=response.read(2200000)
        if len(b)>2100000:raise ValueError('Too much response data')
        return json.loads(b)

def extract(data):
    """Parse V2 envelope; no assumptions that all series have complete data."""
    if not isinstance(data,dict):raise ValueError('Not a v2 envelope')
    stamps=data.get('timestamps') or data.get('unix_seconds') or data.get('time')
    series=data.get('series')
    if not isinstance(stamps,list) or not isinstance(series,list) or not stamps or not series:
        raise ValueError('V2 series/timestamps absent')
    found=[]
    for row in series:
        if not isinstance(row,dict):continue
        vals=row.get('data')
        if vals is None:vals=row.get('values')
        if vals is None:vals=row.get('value')
        if not isinstance(vals,list):continue
        pairs=[]
        for t,v in zip(stamps,vals):
            normalized=iso(t);nv=numeric(v)
            if normalized and nv is not None:pairs.append({'time':normalized,'value':nv})
        if pairs:
            label=str(row.get('name') or row.get('label') or row.get('id') or row.get('type') or 'series')
            found.append({'name':label[:90],'unit':str(row.get('unit') or data.get('unit') or '')[:22],
                          'count':len(pairs),'latest':pairs[-1],'peak':max(pairs,key=lambda p:abs(p['value']))})
    if not found:raise ValueError('No numerical series')
    return found

def europe_grid():
    # These indicators do not constitute a reserve-margin calculation.
    today=dt.datetime.now(UTC).date()
    since=(today-dt.timedelta(days=1)).isoformat()
    until=(today+dt.timedelta(days=2)).isoformat()
    specs=[
        ('hu_load_forecast','Magyarország terhelési előrejelzése',
         'public_power_forecast',{'country':'hu','production_type':'load','forecast_type':'day-ahead','start':since,'end':until}),
        ('hu_physical_flows','Magyarország határkeresztező fizikai áramlásai',
         'cbpf',{'country':'hu','start':since,'end':today.isoformat()}),
        ('eu_renewable_share','Európai megújulóenergia-arány előrejelzése',
         'ren_share_forecast',{'country':'eu'}),
    ]
    readings=[];problems=[]
    for code,title,endpoint,params in specs:
        try:
            raw=get(BASE+endpoint+'?'+urlencode(params));series=extract(raw)
            readings.append({'key':code,'name':title,'series':series[:14],
                             'available_until':raw.get('available_until'),
                             'source_url':BASE+endpoint+'?'+urlencode(params)})
        except Exception as exc:problems.append({'key':code,'reason':str(exc)[:170]})
    if not readings:raise ValueError('Európai villamosenergia kontextus nem elérhető: '+str(problems)[:230])
    return {'updated_at':dt.datetime.now(UTC).isoformat(),'readings':readings,'partial_errors':problems,
            'scope':'HU fizikai energiaáramlások és előrejelzett fogyasztás; EU megújulóenergia-arány',
            'warning':'NEM ENTSO-E STA / kapacitásmegfelelőségi eredmény; nem blackout-esély.',
            'source':'Energy-Charts / Fraunhofer ISE (CC BY 4.0)'}
