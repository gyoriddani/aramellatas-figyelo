import datetime as dt
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from collect import parse_noaa_kp
from health import inspect
UTC=dt.timezone.utc
T=dt.datetime(2026,11,17,13,tzinfo=UTC)
class Fixes(unittest.TestCase):
    def test_noaa_2026_array_of_objects(self):
        rows=[{'time_tag':'2026-11-17T12:00:00','kp':3.67,'observed':'predicted'},
              {'time_tag':'2026-11-17T15:00:00','kp':4.33,'observed':'predicted'}]
        r=parse_noaa_kp(rows)
        self.assertEqual(len(r),2)
        self.assertEqual(r[1]['kp'],4.33)
        self.assertEqual(r[0]['time'],'2026-11-17T12:00:00Z')
    def test_noaa_legacy_format(self):
        rows=[['time_tag','kp'],['2026-11-17 12:00:00','6.0']]
        self.assertEqual(parse_noaa_kp(rows)[0]['kp'],6.0)
    def test_cached_but_failed_is_failure(self):
        d={'feeds':{'weather':{'updated_at':T.isoformat(),'hours':[]}},'errors':{'weather':'HTTP 502'}}
        r=inspect(d,T)
        self.assertEqual(next(x for x in r['items'] if x['key']=='weather')['status'],'failed')
    def test_optional_key_is_not_core(self):
        d={'feeds':{},'errors':{'gie_storage':'GIE_API_KEY GitHub Secret nincs megadva (opcionális)'}}
        r=inspect(d,T)
        self.assertEqual(next(x for x in r['items'] if x['key']=='gie_storage')['status'],'not_configured')
        self.assertNotIn('gie_storage',r['important_missing'])
if __name__=='__main__':unittest.main()
