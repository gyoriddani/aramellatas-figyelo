import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from assess import evaluate
from backtest import evaluate as test_history
from grid import extract
from cap import parse_cap
from health import inspect
from notify import health_problem,eligible

UTC=dt.timezone.utc
T=dt.datetime(2026,11,17,10,tzinfo=UTC)

class V4Tests(unittest.TestCase):
    def test_horizons_independent(self):
        weather={'updated_at':T.isoformat(),'hours':[
          {'time':(T+dt.timedelta(hours=36)).astimezone(dt.timezone(dt.timedelta(hours=1))).replace(tzinfo=None).isoformat(),
           'temperature_c':-1,'gust_kmh':100,'precip_mm':0,'snow_cm':0}]}
        d={'feeds':{'weather':weather}}
        a=evaluate(d,{'alerts':[]},T,24)
        b=evaluate(d,{'alerts':[]},T,48)
        self.assertIsNone(next(c for c in a['categories'] if c['key']=='local_power')['score'])
        self.assertGreater(next(c for c in b['categories'] if c['key']=='local_power')['score'],50)
    def test_freshness_missing_is_not_zero(self):
        h=inspect({'feeds':{}},T)
        self.assertEqual(h['important_fresh'],0)
        self.assertTrue(h['degraded'])
        self.assertTrue(health_problem({'health':h},{},T))
    def test_cap_actual_ends_in_future(self):
        cap=b'''<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2"><status>Actual</status><msgType>Alert</msgType>
        <info><severity>Severe</severity><event>Wind</event><headline>Severe wind</headline>
        <onset>2026-11-17T09:00:00Z</onset><expires>2026-11-17T16:00:00Z</expires>
        <area><areaDesc>Hajdu-Bihar</areaDesc></area></info></alert>'''
        items=parse_cap(cap,'HU','https://feeds.meteoalarm.org/example')
        self.assertEqual(len(items),1)
        d={'feeds':{'cap_warnings':{'updated_at':T.isoformat(),'alerts':items}}}
        a=evaluate(d,{'alerts':[]},T)
        c=next(c for c in a['categories'] if c['key']=='extreme_weather')
        local=next(c for c in a['categories'] if c['key']=='local_power')
        self.assertEqual(c['score'],65)
        self.assertEqual(c['status'],'official_cap')
        self.assertIsNone(local['score'])
        self.assertEqual(eligible(a,{'sent':{}},T)[0]['key'],'extreme_weather')
        bad=cap.replace(b'Actual',b'Test')
        self.assertEqual(parse_cap(bad,'HU','https://feeds.meteoalarm.org/example'),[])
    def test_v2_parser(self):
        f={'timestamps':['2026-11-17T10:00:00Z','2026-11-17T11:00:00Z'],
           'series':[{'id':'HU','unit':'MW','data':[1000,1200]}]}
        r=extract(f)
        self.assertEqual(r[0]['latest']['value'],1200)
    def test_historical_precision(self):
        h=test_history([{'outcome':1,'index_score':70},{'outcome':0,'index_score':70},
                        {'outcome':0,'index_score':20},{'outcome':1,'index_score':20}])
        self.assertEqual(h['precision'],0.5)
        self.assertEqual(h['recall'],0.5)

if __name__=='__main__':unittest.main()
