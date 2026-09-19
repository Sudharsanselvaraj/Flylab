"""Measured full-network physical-key trials; no editor injection or UI shortcuts."""
import argparse,asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services/sim-engine'))
from hawking_fly.physical_coding.session import Session
from hawking_fly.physical_coding.policy import ART
from hawking_fly.coding.core import graph
async def run(case,mode):
    async def report(e):
        if e['kind'] in ('decision','result','abstention'):print(json.dumps({k:v for k,v in e.items() if k in ('kind','id','mode','character','visual_reading','tick','time','success','status','detail','session')}),flush=True)
    target='Hello Fly' if case=='heldout' else 'Hello World'
    silenced=[n['body_id'] for n in graph()['nodes'] if n['input']] if case=='silenced' else []
    s=Session(target,fault=case=='wrong-key',mode=mode,silenced=silenced,emit=report)
    result=await s.run(max_decisions=1 if case=='silenced' else 48);result['session']=s.id
    name={'wrong-key':'evaluation.json','heldout':'heldout.json','silenced':'silencing.json'}[case]
    if mode=='full-precision':name='precision-'+name
    (ART/'full_network'/name).write_text(json.dumps(result,indent=2))
    print('SAVED',s.id,flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=['wrong-key','heldout','silenced'],default='wrong-key');parser.add_argument('--mode',choices=['full-fast','full-precision'],default='full-fast');args=parser.parse_args()
    asyncio.run(run(args.case,args.mode))
