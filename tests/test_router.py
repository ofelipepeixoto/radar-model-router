import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from radar_router.contracts import ContractError, Prediction, RouteInput, Scope, parse_json
from radar_router.policy import decide
from radar_router.ledger import Ledger, LedgerError
from radar_router.service import Router
from radar_router.adapters import Capabilities, hermes_request
BASE = dict(session="session-a", turn="turn-1", task="lookup", risk="low", current_tier=2, continuation=False)

class Contracts(unittest.TestCase):
    def test_metadata_only(self):
        for key in ["prompt", "api_key", "tenant", "paid_enabled"]:
            with self.subTest(key=key), self.assertRaises(ContractError):RouteInput.from_dict({**BASE,key:"SECRET_SYNTHETIC"})
    def test_missing_field(self):
        value=dict(BASE);del value['risk']
        with self.assertRaises(ContractError):RouteInput.from_dict(value)
    def test_bad_identifier(self):
        for value in ['', 'a'*65, 'private prompt', '../x',None]:
            with self.subTest(value=value),self.assertRaises(ContractError):RouteInput.from_dict({**BASE,'session':value})
    def test_bool_tier(self):
        with self.assertRaises(ContractError):RouteInput.from_dict({**BASE,'current_tier':True})
    def test_continuation_boolean(self):
        with self.assertRaises(ContractError):RouteInput.from_dict({**BASE,'continuation':'false'})
    def test_unhashable_task(self):
        with self.assertRaises(ContractError):RouteInput.from_dict({**BASE,'task':[]})
    def test_nonfinite_json(self):
        for value in [b'{"x":NaN}',b'{"x":Infinity}',b'{"x":-Infinity}']:
            with self.subTest(value=value),self.assertRaises(ContractError):parse_json(value)
    def test_duplicate_json(self):
        with self.assertRaises(ContractError):parse_json(b'{"task":"lookup","task":"analysis"}')
    def test_payload_limit(self):
        with self.assertRaises(ContractError):parse_json(b' '*8193)
    def test_bad_encoding(self):
        with self.assertRaises(ContractError):parse_json(b'\xff')
    def test_invalid_distribution(self):
        for values in [(4,-3,0,0),(.1,.1,.1,.1),(True,0,0,0),(float('nan'),0,0,0),(.5,.5,0)]:
            with self.subTest(values=values),self.assertRaises(ContractError):Prediction(values,1,0,0)
    def test_invalid_scores(self):
        for value in [True,-1,4,float('inf')]:
            with self.subTest(value=value),self.assertRaises(ContractError):Prediction((1,0,0,0),value,0,0)

class Policy(unittest.TestCase):
    def route(self,prediction=None,scope=None,**changes):return decide(RouteInput.from_dict({**BASE,**changes}),scope or Scope('tenant'),prediction)
    def test_static_tiers(self):
        for task,tier in [('lookup',0),('draft',1),('analysis',2),('architecture',3)]:
            with self.subTest(task=task):self.assertEqual(self.route(task=task).tier,tier)
    def test_continuation_holds(self):self.assertEqual(self.route(continuation=True).tier,2)
    def test_high_risk_forces_review(self):
        d=self.route(risk='high',current_tier=0);self.assertEqual((d.tier,d.effort,d.review_required),(3,'xhigh',True))
    def test_trusted_scope_cannot_be_lowered(self):
        d=self.route(scope=Scope('tenant',3,True),current_tier=0);self.assertEqual((d.tier,d.review_required),(3,True))
    def test_minimum_effort(self):self.assertEqual(self.route(scope=Scope('tenant',2)).effort,'high')
    def test_predictor_cannot_lower_continuation(self):self.assertEqual(self.route(Prediction((1,0,0,0),0,0,0),continuation=True).tier,2)
    def test_predictor_cannot_lower_risk(self):self.assertEqual(self.route(Prediction((1,0,0,0),0,0,0),risk='high').tier,3)
    def test_predicted_stakes_raise_light(self):
        d=self.route(Prediction((1,0,0,0),0,0,.8),current_tier=0);self.assertTrue(d.review_required);self.assertEqual(d.tier,3)
    def test_offline_by_default(self):
        d=self.route().to_dict();self.assertTrue(d['shadow']);self.assertFalse(d['paid_enabled'])

class State(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.ledger=Ledger(self.tmp.name);self.router=Router(self.ledger)
    def test_idempotency(self):
        calls=[];key=self.ledger.identity('a','b','c')
        def factory():calls.append(1);return {'tier':1}
        self.assertEqual(self.ledger.get_or_create(key,'fp',factory),self.ledger.get_or_create(key,'fp',factory));self.assertEqual(len(calls),1)
    def test_changed_input_rejected(self):
        self.router.route(BASE,Scope('a'))
        with self.assertRaises(LedgerError):self.router.route({**BASE,'task':'analysis'},Scope('a'))
    def count(self):
        with self.ledger.connect() as db:return db.execute('SELECT COUNT(*) FROM decisions').fetchone()[0]
    def test_distinct_sessions(self):
        self.router.route(BASE,Scope('a'));self.router.route({**BASE,'session':'session-b','task':'analysis'},Scope('a'));self.assertEqual(self.count(),2)
    def test_distinct_tenants(self):self.router.route(BASE,Scope('a'));self.router.route(BASE,Scope('b'));self.assertEqual(self.count(),2)
    def test_restart(self):self.assertEqual(self.router.route(BASE,Scope('a')),Router(Ledger(self.tmp.name)).route(BASE,Scope('a')))
    def test_exact_prediction_fingerprint(self):
        self.router.route(BASE,Scope('a'),Prediction((.60001,.39999,0,0),0,0,0))
        with self.assertRaises(LedgerError):self.router.route(BASE,Scope('a'),Prediction((.60002,.39998,0,0),0,0,0))
    def test_concurrent_single_factory(self):
        calls=[]
        def action(_):return self.ledger.get_or_create('key','fp',lambda:(calls.append(1) or {'tier':1}))
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(action,range(16)))
        self.assertEqual(len(calls),1);self.assertEqual(len(results),16)
    def test_expiry(self):
        with patch('radar_router.ledger.time.time',return_value=100):self.router.route(BASE,Scope('a'))
        with patch('radar_router.ledger.time.time',return_value=100+7*86400+1):d=self.router.route({**BASE,'task':'analysis'},Scope('a'))
        self.assertEqual(d['tier'],2)
    def test_no_raw_identity(self):
        self.router.route(BASE,Scope('TENANT_SYNTHETIC'))
        with self.ledger.connect() as db:rows=str(db.execute('SELECT * FROM decisions').fetchall())
        for value in ['TENANT_SYNTHETIC','session-a','turn-1']:self.assertNotIn(value,rows)
    def test_private_permissions(self):
        for name in ['identity.key','ledger.sqlite3']:self.assertEqual((Path(self.tmp.name)/name).stat().st_mode&0o777,0o600)
    def test_symlink_rejected(self):
        other=Path(self.tmp.name)/'other';other.mkdir();(other/'ledger.sqlite3').symlink_to(Path(self.tmp.name)/'ledger.sqlite3')
        with self.assertRaises(LedgerError):Ledger(other)

class Budget(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.ledger=Ledger(self.tmp.name)
    def reserve(self,operation,maximum=60,limit=100,tenant='a'):return self.ledger.reserve(tenant,operation,maximum,limit,paid_enabled=True)
    def test_disabled(self):
        with self.assertRaises(LedgerError):self.ledger.reserve('a','op',1,100)
    def test_concurrent_budget(self):
        def action(i):
            try:self.reserve('op-'+str(i));return True
            except LedgerError:return False
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(action,range(12)))
        self.assertEqual(sum(results),1)
    def test_duplicate(self):
        self.reserve('op')
        with self.assertRaises(LedgerError):self.reserve('op')
    def test_unknown_keeps_budget(self):
        key=self.reserve('op');self.ledger.reconcile(key)
        with self.assertRaises(LedgerError):self.reserve('other')
    def test_actual_releases_unused(self):key=self.reserve('op');self.ledger.reconcile(key,20);self.reserve('other',80)
    def test_restart_keeps_reservation(self):
        self.reserve('op');new=Ledger(self.tmp.name)
        with self.assertRaises(LedgerError):new.reserve('a','other',60,100,paid_enabled=True)
    def test_late_reconcile(self):key=self.reserve('op');self.ledger.reconcile(key);self.ledger.reconcile(key,0);self.reserve('other',100)
    def test_reconciliation_conflict(self):
        key=self.reserve('op');self.ledger.reconcile(key,10);self.ledger.reconcile(key,10)
        with self.assertRaises(LedgerError):self.ledger.reconcile(key,0)
    def test_overrun_recorded(self):
        key=self.reserve('op')
        with self.assertRaisesRegex(LedgerError,'overrun'):self.ledger.reconcile(key,150)
        with self.assertRaises(LedgerError):self.reserve('other',1)
        with self.ledger.connect() as db:self.assertEqual(db.execute('SELECT actual FROM reservations').fetchone()[0],150)
    def test_tenant_budget_isolation(self):self.reserve('one',100,tenant='a');self.reserve('one',100,tenant='b')
    def test_no_auto_expiration(self):
        self.reserve('one',100)
        with patch('radar_router.ledger.time.time',return_value=10**10):
            with self.assertRaises(LedgerError):self.reserve('two',1)
    def test_invalid_amounts(self):
        for value in [-1,True,0]:
            with self.subTest(value=value),self.assertRaises(ContractError):self.reserve('op',value)

class Adapter(unittest.TestCase):
    def setUp(self):
        self.cap=Capabilities('offline','local',('demo-light','demo-standard','demo-deep','demo-review'),(100,200,300,400))
        self.result=decide(RouteInput.from_dict(BASE),Scope('a')).to_dict();self.request={'model':'demo-deep','max_tokens':900,'messages':[{'role':'user','content':'SYNTHETIC'}]}
    def apply(self,**changes):
        args=dict(provider='offline',api_mode='local',request=self.request,capabilities=self.cap,enabled=True);args.update(changes);return hermes_request(self.result,**args)
    def test_provider_mode_gated(self):self.assertIsNone(self.apply(provider='other'));self.assertIsNone(self.apply(api_mode='oauth'))
    def test_disabled(self):self.assertIsNone(self.apply(enabled=False))
    def test_review_blocks(self):self.result['review_required']=True;self.assertIsNone(self.apply())
    def test_unknown_model(self):self.assertIsNone(self.apply(request={'model':'unknown'}))
    def test_clamps_and_preserves(self):
        original=json.loads(json.dumps(self.request));result=self.apply()['request'];self.assertEqual(result['model'],'demo-light');self.assertEqual(result['max_tokens'],100);self.assertEqual(result['messages'],original['messages']);self.assertEqual(self.request,original)
    def test_bad_tokens(self):
        with self.assertRaises(ContractError):self.apply(request={'model':'demo-deep','max_tokens':True})
    def test_no_effort_guess(self):self.assertNotIn('reasoning',self.apply()['request'])

class CLI(unittest.TestCase):
    def run_cli(self,payload):
        with tempfile.TemporaryDirectory() as state:return subprocess.run([sys.executable,'-m','radar_router.cli','--state-dir',state],input=payload,capture_output=True)
    def test_success(self):
        r=self.run_cli(json.dumps(BASE).encode());self.assertEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['tier'],0)
    def test_reject_no_echo(self):
        r=self.run_cli(json.dumps({**BASE,'prompt':'SECRET_SYNTHETIC'}).encode());self.assertEqual(r.returncode,2);self.assertNotIn(b'SECRET_SYNTHETIC',r.stderr+r.stdout)

if __name__=='__main__':unittest.main()
