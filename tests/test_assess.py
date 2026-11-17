import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from assess import evaluate, weather_score, THRESHOLD
from notify import eligible, compose

UTC=dt.timezone.utc
NOW=dt.datetime(2026,11,17,10,0,tzinfo=UTC)

def dfeed(hours=None,kp=None,ews=None,age=0):
    feeds={}
    if hours is not None:feeds['weather']={'updated_at':(NOW-dt.timedelta(hours=age)).isoformat(),'hours':hours}
    if kp is not None:feeds['space_weather']={'updated_at':NOW.isoformat(),'kp':kp}
    if ews is not None:feeds['ews']=ews
    return {'feeds':feeds}

def hour(gust=20,ts=NOW+dt.timedelta(hours=2),mm=0,snow=0,temp=5):
    local=ts.astimezone(dt.timezone(dt.timedelta(hours=1))).replace(tzinfo=None)
    return {'time':local.isoformat(timespec='minutes'),'gust_kmh':gust,'precip_mm':mm,'snow_cm':snow,'temperature_c':temp}

class ModelTests(unittest.TestCase):
    def test_no_data_is_not_zero(self):
        r=evaluate({'feeds':{}},{'alerts':[]},NOW)
        self.assertIsNone(r['overall']['score'])
        self.assertEqual(r['overall']['coverage'],0)
        self.assertEqual(r['alerts'],[])
        self.assertEqual(len(r['categories']),13)
    def test_weather_window_score_and_alert(self):
        d=dfeed([hour(gust=70,snow=.5),hour(gust=110,ts=NOW+dt.timedelta(hours=36))])
        r=evaluate(d,{'alerts':[]},NOW)
        c=next(x for x in r['categories'] if x['key']=='local_power')
        self.assertTrue(50<=c['score']<100)
        self.assertIn('local_power',r['alerts'])
        self.assertIsNone(c['probability_pct'])
    def test_weather_old_not_inferred_zero(self):
        r=evaluate(dfeed([hour(gust=90)],age=48),{'alerts':[]},NOW)
        c=next(x for x in r['categories'] if x['key']=='local_power')
        self.assertIsNone(c['score'])
    def test_no_ews_influence_on_category(self):
        r=evaluate(dfeed(ews={'updated_at':NOW.isoformat(),'level':5}),{'alerts':[]},NOW)
        self.assertIsNone(r['overall']['score'])
    def test_space_weather(self):
        r=evaluate(dfeed(kp=[{'time':(NOW+dt.timedelta(hours=1)).isoformat(),'kp':8}]),{'alerts':[]},NOW)
        c=next(x for x in r['categories'] if x['key']=='geomagnetic')
        self.assertEqual(c['score'],90)
        self.assertIsNone(c['probability_pct'])
    def test_official_verified_notice(self):
        base={'category':'fuel','severity':'severe','title':'Teszt üzemanyagellátási figyelmeztetés',
              'url':'https://example.gov.hu/example','verified':True,'scope':'Magyarország',
              'start_at':NOW.isoformat(),'expires_at':(NOW+dt.timedelta(hours=5)).isoformat()}
        r=evaluate({'feeds':{}},{'alerts':[base]},NOW)
        c=next(x for x in r['categories'] if x['key']=='fuel')
        self.assertEqual(c['score'],75)
        self.assertEqual(c['status'],'verified_notice')
        self.assertIn('fuel',r['alerts'])
        r2=evaluate({'feeds':{}},{'alerts':[{**base,'verified':False}]},NOW)
        self.assertIsNone(next(x for x in r2['categories'] if x['key']=='fuel')['score'])
    def test_emailed_only_one_per_24h_unless_escalates(self):
        c={'key':'local_power','name':'Helyi áramszünet','score':65,'status':'estimated_index','evidence':[]}
        a={'categories':[c],'overall':{'coverage':1,'total_categories':13}}
        self.assertEqual(len(eligible(a,{'sent':{}},NOW)),1)
        self.assertEqual(eligible(a,{'sent':{'local_power':{'at':(NOW-dt.timedelta(hours=1)).isoformat(),'score':65}}},NOW),[])
        self.assertEqual(len(eligible(a,{'sent':{'local_power':{'at':(NOW-dt.timedelta(hours=1)).isoformat(),'score':60}}},NOW)),1)
        self.assertEqual(eligible(a,{'sent':{}},NOW)[0]['score'],65)
    def test_email_contains_no_blackout_probability(self):
        c={'key':'geomagnetic','name':'Geomágneses vihar','score':90,'status':'estimated_index','evidence':[],'peak_time':NOW.isoformat()}
        message=compose([c],{'overall':{'coverage':1,'total_categories':13}},NOW,'example@example.com')
        self.assertIn('NEM 50%',message.get_content())

if __name__=='__main__': unittest.main()
