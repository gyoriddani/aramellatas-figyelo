#!/usr/bin/env python3
"""Check historical alert performance on REAL labeled outage outcomes.
The score is an alert index, not a probability. No labeled data -> no result.
Expected CSV: issued_at,category,horizon_hours,index_score,outcome (0/1).
One prediction row must be recorded BEFORE outcome is known.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HISTORY=ROOT/'data/outcomes.csv'
REPORT=ROOT/'data/backtest_report.json'

def evaluate(rows,threshold=50):
    counts={'tp':0,'fp':0,'tn':0,'fn':0}
    for row in rows:
        outcome=int(row['outcome'])
        score=float(row['index_score'])
        if not 0<=score<=100 or outcome not in (0,1):raise ValueError('Invalid outcome or index')
        # Count only outcomes with known event status. Index is not a percentage.
        predicted=score>=threshold
        counts['tp' if predicted and outcome else 'fp' if predicted else 'fn' if outcome else 'tn']+=1
    tp,fp,tn,fn=(counts[x] for x in ('tp','fp','tn','fn'))
    div=lambda a,b:round(a/b,4) if b else None
    return {**counts,'n':sum(counts.values()),'threshold_index':threshold,
            'precision':div(tp,tp+fp),'recall':div(tp,tp+fn),
            'false_positive_rate':div(fp,fp+tn),'note':'Not event probability; historical threshold validation only.'}

def main():
    if not HISTORY.exists():
        print('Nincs valós, címkézett eseményadat. A modell nem tekinthető validáltnak.');return
    with HISTORY.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    if not rows:
        print('Üres eseménynapló; nincs értelmezhető pontossági mérés.');return
    required={'issued_at','category','horizon_hours','index_score','outcome'}
    if not required.issubset(rows[0]):raise ValueError('Invalid CSV columns')
    outcome=evaluate(rows)
    REPORT.write_text(json.dumps(outcome,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(outcome,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
