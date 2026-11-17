"""Prospective, time-stamped forecasts for later event outcome validation."""
import csv
import datetime as dt
from pathlib import Path

DEST=Path(__file__).resolve().parents[1]/'data'/'predictions.csv'
FIELDS=('issued_at','category','horizon_hours','index_score','peak_time','status')

def record(assessment):
    previous=[]
    if DEST.exists():
        with DEST.open(encoding='utf-8',newline='') as f:
            previous=list(csv.DictReader(f))
    # Keep ~90 days of 3-hourly snapshots for 13 categories, three horizons.
    # Store every non-NA signal for future matching against independently verified actual events.
    out=[];stamp=assessment.get('generated_at')
    for horizon,chunk in (assessment.get('windows') or {}).items():
        for row in chunk.get('categories',[]):
            score=row.get('score')
            if score is None:continue
            out.append({'issued_at':stamp,'category':row['key'],'horizon_hours':horizon,
                        'index_score':score,'peak_time':row.get('peak_time') or '',
                        'status':row.get('status') or ''})
    oldkeys={(r.get('issued_at'),r.get('category'),r.get('horizon_hours')) for r in previous}
    previous += [r for r in out if (r['issued_at'],r['category'],r['horizon_hours']) not in oldkeys]
    previous=previous[-8000:]
    DEST.parent.mkdir(parents=True,exist_ok=True)
    with DEST.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(previous)
    return len(out)
