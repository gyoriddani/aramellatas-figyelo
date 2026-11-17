#!/usr/bin/env python3
"""GitHub Actions summary: identify actual source failures vs optional unconfigured sources."""
from __future__ import annotations
import json
import os
from pathlib import Path
from health import inspect, IMPORTANT
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'latest.json'

def main():
    if not DATA.exists():
        print('HIBA: data/latest.json hiányzik.');return
    data=json.loads(DATA.read_text(encoding='utf-8'))
    health=(data.get('assessment') or {}).get('health') or inspect(data)
    rows=['## Adatforrások – részletes állapot', '',
          '| Forrás | Állapot | Legutóbbi frissítés | Hiba / részleges eredmény |',
          '|:--|:--|:--|:--|']
    for x in health.get('items',[]):
        key=x['key'];feed=data.get('feeds',{}).get(key) or {}
        partial=feed.get('partial_errors',[])
        ex=x.get('error') or ''
        if partial:
            ex+=' | Részleges: '+str(partial[:3])[:240]
        ex=ex.replace('|','/').replace('\n',' ')
        line='| '+key+' | '+x['status']+' | '+str(x.get('updated_at') or '—')+' | '+(ex or '—')+' |'
        rows.append(line)
    rows+=['','Az **optional/not_configured** státusz nem rendszerhiba. A `failed` tényleges lekérdezési hiba; a `partial` csak részben sikeres válasz.','','A NOAA SWPC JSON 2026-os új formátumát a V4.1 már kezeli.']
    body='\n'.join(rows)+'\n'
    print(body)
    file=os.getenv('GITHUB_STEP_SUMMARY')
    if file:
        with open(file,'a',encoding='utf-8') as f:f.write(body)

if __name__=='__main__':main()
