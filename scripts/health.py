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
        err=str(failures.get(key,''))[:180]
        optional_not_set=(key in ('gie_storage','entsoe_hu_load') and
                          'GitHub Secret nincs megadva' in err)
        partial=feed.get('partial_errors',[]) if isinstance(feed,dict) else []
        # An old but still recent cached feed must not hide the latest failed fetch.
        if optional_not_set:
            status='not_configured'
        elif err:
            status='failed'
        elif age_ok(feed,at):
            status='partial' if partial else 'fresh'
        else:
            status='unavailable'
        items.append({'key':key,'required':key in IMPORTANT,
                      'status':status,'error':err or None,
                      'partial_error_count':len(partial) if isinstance(partial,list) else 0,
                      'updated_at':feed.get('updated_at') if isinstance(feed,dict) else None})
    req=[x for x in items if x['required']]
    stale=[x['key'] for x in req if x['status'] not in ('fresh','partial')]
    return {'checked_at':at.isoformat(),'important_total':len(req),
            'important_fresh':len(req)-len(stale),'important_missing':stale,
            'items':items,'degraded':len(stale)>=2,
            'note':'Az adatgyűjtés hibája nem jelenti azt, hogy nincs veszély.'}
