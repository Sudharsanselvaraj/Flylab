"""Real Chromium episodes: acceptance, fault recovery, held-out and perturbation."""
import asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services/sim-engine'))
from hawking_fly.physical_coding.session import Session
from hawking_fly.physical_coding.policy import ART
from hawking_fly.coding.core import graph

async def evaluate():
    reports=[]
    inputs=[n['body_id'] for n in graph()['nodes'] if n['input']]
    cases=[('normal','Hello World',False,[]),('wrong-key','Hello World',True,[]),('held-out','Hello Fly',False,[]),('held-out','Fly World',False,[]),('validation','Green Lab',False,[]),('silenced','Hello World',False,inputs),('restored','Hello World',False,[])]
    for condition,target,fault,silenced in cases:
        s=Session(target,silenced,fault)
        try:result=await s.run()
        except ValueError as exc:result={'target':target,'success':False,'corrections':0,'status':'abstained','detail':str(exc),'checkpoint_sha256':s.controller.sha}
        reports.append({'condition':condition,'session':s.id,**result});print(json.dumps(reports[-1]),flush=True)
    normal=json.loads((ART/'sessions'/reports[0]['session']/'episode.json').read_text())
    restored=json.loads((ART/'sessions'/reports[-1]['session']/'episode.json').read_text())
    exact=normal['decisions']==restored['decisions']
    report={'scope':'Single-line headings; held-out word composition, not unseen syntax or layout','episodes':reports,'restored_decisions_exact':exact}
    (ART/'evaluation.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':asyncio.run(evaluate())
