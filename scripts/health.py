"""Monitor collection quality. Missing source is unknown, not low risk."""
from __future__ import annotations
import datetime as dt
from assess import age_ok

UTC=dt.timezone.utc
IMPORTANT=('weather','electricity','space_weather','european_prices','europe_weather','meteoalarm')
OPTIONAL=('ews','official_news','gie_storage','entsoe_hu_load','grid_context','cap_warnings')

def inspect(data,at=None):
    at=at or dt.datetime.now(UTC)
    feeds=data.get('feeds',{});failures=data.get('errors',{});items=[]
    for key in IMPORTANT+OPTIONAL:
        feed=feeds.get(key)
        fresh=age_ok(feed,at)
        items.append({'key':key,'required':key in IMPORTANT,
                      'status':'fresh' if fresh else 'unavailable',
                      'error':str(failures.get(key,''))[:180] or None,
                      'updated_at':feed.get('updated_at') if isinstance(feed,dict) else None})
    req=[x for x in items if x['required']]
    stale=[x['key'] for x in req if x['status']!='fresh']
    return {'checked_at':at.isoformat(),'important_total':len(req),
            'important_fresh':len(req)-len(stale),'important_missing':stale,
            'items':items,'degraded':len(stale)>=2,
            'note':'Az adatgyűjtés hibája nem jelenti azt, hogy nincs veszély.'}
