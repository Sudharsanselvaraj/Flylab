"""Coding session protocol: inference accepts pixels only; privileged training isolated."""
import asyncio,itertools,json,threading,hashlib,re
from typing import Literal
from fastapi import APIRouter,HTTPException,WebSocket,WebSocketDisconnect,Request
from fastapi.responses import FileResponse
from pydantic import BaseModel,ConfigDict,Field
from hawking_fly.coding.core import ART,ACTIONS,BASE,DT,STEPS,Policy,graph,source_for,split,digest

router=APIRouter(prefix='/api/coding')
training_lock=threading.Lock()
training_cancel=threading.Event()
class Observation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:Literal['observe']='observe'
    tick:int=Field(ge=0)
    pixels:list[int]=Field(min_length=2304,max_length=2304)
class Ack(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:Literal['ack']='ack'
    tick:int=Field(ge=0)
    events:list[dict]=Field(max_length=4096)
    revision:int=Field(ge=0)

@router.get('/catalog')
def catalog():
    manifest=ART/'training_manifest/manifest.json'
    return {'graph':graph(),'actions':ACTIONS,'base':BASE,'dt':DT,'manifest':json.loads(manifest.read_text()) if manifest.exists() else None,'tasks':[{'id':i,'state':t,'split':split(t),'source':source_for(t)} for i,t in enumerate(itertools.product(range(2,5),repeat=3))],'curriculum':[{'state':s,'source':source_for(s)} for s in itertools.product(range(5),repeat=3)]}

@router.get('/training')
def training_status():
    p=ART/'metrics/status.json';return json.loads(p.read_text()) if p.exists() else {'state':'untrained'}

@router.post('/training')
def start_training(data:dict):
    if not training_lock.acquire(blocking=False):raise HTTPException(409,'Training already running')
    training_cancel.clear()
    try:
        pages=data.get('pages',[])
        if len(pages)!=125:raise ValueError('125 actual browser captures required')
        from hawking_fly.coding.training import compose,train
        from hawking_fly.coding.core import pixels_to_features
        for page in pages:pixels_to_features(compose(page['pixels'],page['pixels']))
        (ART/'captures.json').write_text(json.dumps(data))
        (ART/'metrics').mkdir(exist_ok=True)
        (ART/'metrics/status.json').write_text(json.dumps({'state':'starting'}))
        def work():
            try:train(cancelled=training_cancel.is_set)
            except Exception as exc:(ART/'metrics/status.json').write_text(json.dumps({'state':'error','detail':str(exc)}))
            finally:training_lock.release()
        threading.Thread(target=work,daemon=True).start()
        return {'state':'starting'}
    except Exception as exc:
        training_lock.release();raise HTTPException(400,str(exc))

@router.post('/training/cancel')
def cancel_training():
    training_cancel.set();return {'state':'cancelling'}

@router.get('/evaluation')
def evaluation(full:bool=False):
    path=ART/'metrics/browser_evaluation.json'
    if not path.exists():return {'available':False}
    data=json.loads(path.read_text())
    if full:return data
    return {'available':True,'success_rate':data['success_rate'],'episodes':len(data['episodes']),'exact_replay':data['replay']['exact'],'perturbed_success':data['perturbation']['result']['success']}

@router.post('/evaluation')
def save_evaluation(data:dict):
    # Evaluator result is an artifact, never passed to Policy.infer.
    if len(json.dumps(data))>15_000_000:raise HTTPException(413)
    (ART/'metrics').mkdir(exist_ok=True)
    (ART/'metrics/browser_evaluation.json').write_text(json.dumps(data,separators=(',',':')))
    return {'stored':True,'sha256':digest(data)}

@router.post('/recording')
async def save_recording(request:Request):
    chunks=[];size=0
    async for chunk in request.stream():
        size+=len(chunk)
        if size>100_000_000:raise HTTPException(413,'Recording exceeds 100 MB')
        chunks.append(chunk)
    raw=b''.join(chunks)
    if not raw.startswith(bytes.fromhex('1a45dfa3')):raise HTTPException(400,'Expected WebM recording')
    sha=hashlib.sha256(raw).hexdigest();folder=ART/'recordings';folder.mkdir(exist_ok=True)
    (folder/f'{sha}.webm').write_bytes(raw)
    return {'url':f'/api/coding/recording/{sha}.webm','sha256':sha,'bytes':size}

@router.get('/recording/{name}')
def recording(name:str):
    if not re.fullmatch(r'[0-9a-f]{64}\.webm',name):raise HTTPException(404)
    path=ART/'recordings'/name
    if not path.exists():raise HTTPException(404)
    return FileResponse(path,media_type='video/webm')

@router.websocket('/stream')
async def stream(ws:WebSocket):
    await ws.accept()
    try:
        config=await ws.receive_json()
        if set(config)-{'seed','silenced'}:raise ValueError('Session config accepts seed and silenced neuron IDs only')
        policy=await asyncio.to_thread(Policy)
        silenced=[str(v) for v in config.get('silenced',[])]
        if not set(silenced)<={n['body_id'] for n in policy.g['nodes']}:raise ValueError('Unknown silenced neuron')
        tick=0;pending=None;records=[]
        await ws.send_json({'kind':'ready','checkpoint':policy.sha,'graph':policy.g['sha256'],'tick':0,'dt':DT,'silenced':silenced})
        while True:
            msg=await ws.receive_json()
            if msg.get('kind')=='observe':
                observation=Observation.model_validate(msg)
                if pending is not None or observation.tick!=tick:raise ValueError('Observation out of order or unacknowledged motor action')
                action,neural,logits=await asyncio.to_thread(policy.infer,observation.pixels,silenced,tick)
                tick+=STEPS;pending=action
                record={'kind':'decision','tick':tick,'time':tick*DT,'action':action,'label':ACTIONS[action]['name'],'neural':neural,'logits':logits,'observation_sha256':digest(observation.pixels)}
                records.append(record);await ws.send_json(record)
            elif msg.get('kind')=='ack':
                ack=Ack.model_validate(msg)
                if pending is None or ack.tick<tick:raise ValueError('Unexpected acknowledgment')
                if any(e.get('tick',-1)<=tick or e.get('tick',-1)>ack.tick for e in ack.events):raise ValueError('Motor events outside neural decision interval')
                tick=ack.tick;pending=None
                records[-1]['motor_events']=ack.events;records[-1]['revision']=ack.revision
                await ws.send_json({'kind':'acknowledged','tick':tick})
            elif msg.get('kind')=='save':
                await ws.send_json({'kind':'recording','version':1,'checkpoint':policy.sha,'graph':policy.g['sha256'],'seed':config.get('seed',37),'silenced':silenced,'records':records})
            else:raise ValueError('Unknown message')
    except WebSocketDisconnect:pass
    except Exception as exc:
        await ws.send_json({'kind':'error','detail':str(exc)})
        await ws.close(code=1008)
