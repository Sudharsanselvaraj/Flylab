"""Local, observable optimizer jobs; candidate weights never replace the active policy."""
import asyncio,json,sys,uuid,time,re
from fastapi import APIRouter,HTTPException
from hawking_fly.coding.core import ROOT
from hawking_fly.physical_coding.policy import ART
router=APIRouter(prefix='/api/physical-coding/training')
job=None
async def work(record):
    try:
        extra=['--resume'] if record.get('resume') else []
        process=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'scripts/train_full_cns_readout.py'),'--output',str(ART/'training_runs'/record['id']),*extra,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT,cwd=ROOT)
        record['pid']=process.pid
        async for line in process.stdout:
            try:row=json.loads(line)
            except ValueError:record['last_output']=line.decode().strip()[-500:];continue
            record['events'].append(row)
        record['exit_code']=await process.wait();record['status']='completed' if record['exit_code']==0 else 'failed'
    except Exception as exc:record['status']='failed';record['error']=str(exc)
    finally:
        record['wall_seconds']=time.monotonic()-record.pop('_started')
        path=ART/'training_runs'/record['id'];path.mkdir(exist_ok=True,parents=True);(path/'job.json').write_text(json.dumps(record,indent=2))

@router.post('/start')
async def start(resume_id:str|None=None):
    global job
    if job and job['status']=='running':raise HTTPException(409,'A full-network training job is already running')
    if resume_id and (not re.fullmatch('[a-f0-9]{32}',resume_id) or not (ART/'training_runs'/resume_id/'features.npz').exists()):raise HTTPException(400,'Resume requires a completed candidate with saved features')
    job={'resume':bool(resume_id),'id':resume_id or uuid.uuid4().hex,'status':'running','events':[],'_started':time.monotonic()}
    asyncio.create_task(work(job));return {'id':job['id'],'status':'running'}

@router.get('/status')
def status():return {k:v for k,v in job.items() if not k.startswith('_')} if job else {'status':'idle','events':[]}
