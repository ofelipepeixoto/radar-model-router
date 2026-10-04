"""Synthetic policy correctness, not LLM quality/cost benchmarking."""
import json
from .contracts import RouteInput, Scope
from .policy import decide

def evaluate():
    cases=[('lookup','low',False,2,0,False),('draft','low',False,2,1,False),
           ('analysis','low',False,0,2,False),('architecture','low',False,0,3,False),
           ('lookup','low',True,2,2,False),('lookup','high',False,0,3,True),
           ('draft','high',True,1,3,True),('analysis','low',True,3,3,False)]
    results=[]
    for i,(task,risk,continuation,current,tier,review) in enumerate(cases):
        value=RouteInput.from_dict(dict(session='synthetic',turn=f'case-{i}',task=task,risk=risk,current_tier=current,continuation=continuation))
        d=decide(value,Scope('lab'))
        results.append(d.tier==tier and d.review_required==review)
    return {'kind':'synthetic-policy-correctness','passed':sum(results),'total':len(results),
            'llm_quality_verified':False,'savings_verified':False,'api_calls':0}

def main():
    result=evaluate();print(json.dumps(result,sort_keys=True))
    return 0 if result['passed']==result['total'] else 1

if __name__=='__main__':raise SystemExit(main())
