"""Contact-gated browser sessions. Client never sends code or motor commands."""
import asyncio,base64,gzip,json,re,time,struct
from fastapi import APIRouter,HTTPException,WebSocket,WebSocketDisconnect
from fastapi.responses import FileResponse,Response
from hawking_fly.physical_coding.policy import ART
from hawking_fly.physical_coding.motor import KEYS,DT
from hawking_fly.coding.core import graph
from hawking_fly.physical_coding.session import Session
from hawking_fly.physical_coding.full_network import CACHE

router=APIRouter(prefix='/api/physical-coding')
slots=asyncio.Semaphore(2)
live_sessions={}

@router.get('/catalog')
def catalog():
    manifest=ART/'manifest.json';evaluation=ART/'evaluation.json'
    return {'full_evaluations':[{'condition':name,**json.loads((ART/'full_network'/file).read_text())} for name,file in [('wrong-key acceptance','evaluation.json'),('held-out words','heldout.json'),('visual inputs silenced','silencing.json')] if (ART/'full_network'/file).exists()],'full_network':json.loads((ART/'full_network/manifest.json').read_text()) if (ART/'full_network/manifest.json').exists() else None,'benchmark':json.loads((ART.parent/'full_cns/benchmark.json').read_text()) if (ART.parent/'full_cns/benchmark.json').exists() else None,'keys':KEYS,'dt':DT,'graph':graph(),'manifest':json.loads(manifest.read_text()) if manifest.exists() else None,'evaluation':json.loads(evaluation.read_text()) if evaluation.exists() else None,'targets':[{'label':'Hello World','split':'acceptance'},{'label':'Hello Fly','split':'held-out words'},{'label':'Fly World','split':'held-out words'}]}

@router.get('/sessions')
def saved_sessions():
    rows=[]
    for file in sorted((ART/'sessions').glob('*/episode.json'),key=lambda p:p.stat().st_mtime,reverse=True):
        meta=json.loads(file.read_text());result=meta.get('result')
        if result:rows.append({'session':meta['id'],'mode':meta.get('mode','subgraph'),'target':result['target'],'success':result['success'],'status':result['status'],'corrections':result['corrections'],'ticks':result['ticks']})
        if len(rows)==30:break
    return rows

@router.get('/full-neuron-ids')
def full_ids():
    import numpy as np
    return Response(np.load(CACHE/'body_ids.npy').astype('<u4').tobytes(),media_type='application/octet-stream')

def folder(session):
    if not re.fullmatch('[a-f0-9]{32}',session):raise HTTPException(404)
    path=ART/'sessions'/session
    if not path.exists():raise HTTPException(404)
    return path

@router.get('/session/{session}/{asset}')
def artifact(session:str,asset:str):
    path=folder(session)
    if asset=='replay':
        with gzip.open(path/'timeline.json.gz','rt') as f:return json.load(f)
    if not re.fullmatch(r'(episode\.json|timeline\.json\.gz|spikes\.bin|activity-[0-9]+\.bin|readout-[0-9]+\.bin|index\.html|project\.zip|[0-9]+-[0-9]+\.png)',asset):raise HTTPException(404)
    if not (path/asset).exists():raise HTTPException(404)
    if asset=='index.html':return Response((path/asset).read_text(),media_type='text/plain')
    return FileResponse(path/asset,filename='project.zip' if asset=='project.zip' else None)

@router.get('/trace/{session}/{body_id}')
def neuron_trace(session:str,body_id:str):
    import numpy as np
    path=folder(session);current=live_sessions.get(session)
    if current:
        ids=[n['body_id'] for n in current.neural.nodes];timeline=current.records
    else:
        meta=json.loads((path/'episode.json').read_text());ids=meta.get('spike_archive',{}).get('neurons',[])
        with gzip.open(path/'timeline.json.gz','rt') as f:timeline=json.load(f)
    if body_id not in ids: return {'body_id':body_id,'simulated':False,'ticks':[],'count':0,'decisions':[]}
    index=ids.index(body_id);file=path/'spikes.bin'
    rows=np.memmap(file,dtype='<u4',mode='r',shape=(file.stat().st_size//8,2)) if file.stat().st_size else np.empty((0,2),'<u4')
    times=rows[rows[:,1]==index,0]
    rates=[]
    for frame in timeline:
        if frame.get('activity_file'):
            with (path/frame['activity_file']).open('rb') as f:
                f.seek(16+index*4);rate=struct.unpack('<f',f.read(4))[0]
            rates.append({'tick':frame['tick'],'hz':rate})
        elif 'rates' in frame:rates.append({'tick':frame['tick'],'hz':frame['rates'][index]})
    decisions=[]
    for event in timeline:
        if event['kind']!='decision':continue
        end=np.searchsorted(times,event['tick'],side='right');begin=np.searchsorted(times,event['tick']-50)
        if end>begin:decisions.append({'id':event['id'],'tick':event['tick'],'mode':event['mode'],'character':event.get('character'),'events_in_preceding_100ms':int(end-begin)})
    return {'body_id':body_id,'simulated':True,'count':len(times),'rates':rates,'ticks':times[-64:].tolist(),'decisions':decisions[-8:],'association':'Temporal window, not causal necessity','dt':DT}

@router.websocket('/stream')
async def stream(ws:WebSocket):
    await ws.accept();session=None;receiver=None
    try:
        config=await ws.receive_json()
        if set(config)-{'target','silenced','fault','mode'}:raise ValueError('Session accepts target text, silenced IDs and experimental fault only')
        mode=config.get('mode','subgraph')
        if mode not in ('subgraph','full-fast','full-precision'):raise ValueError('Unknown dynamics mode')
        target=config.get('target','Hello World')
        if not isinstance(target,str) or not 1<=len(target)<=20 or not all(c.isascii() and (c.isalpha() or c==' ') for c in target):raise ValueError('Target requires 1–20 ASCII letters/spaces')
        silenced=config.get('silenced',[])
        if mode=='subgraph':valid_ids={n['body_id'] for n in graph()['nodes']}
        else:
            import numpy as np
            valid_ids=set(map(str,np.load(CACHE/'body_ids.npy')))
        if not set(silenced)<=valid_ids:raise ValueError('Unknown neuron ID')
        async with slots:
            gate=asyncio.Event();gate.set();acks=asyncio.Queue();disconnected=False;pause_announced=False
            async def checkpoint():
                nonlocal pause_announced
                if disconnected:raise WebSocketDisconnect()
                if pause_announced:return
                if not gate.is_set():
                    start=time.monotonic();pause_announced=True
                    await session.capture()
                    audit=await session.computer.audit()
                    await session.publish({'kind':'audit','source':audit['source'],'revision':audit['revision'],'browser_events':audit['events']})
                    await session.publish({'kind':'paused',**session.neural.frame()})
                    await gate.wait();session.paused_seconds+=time.monotonic()-start;pause_announced=False
                    if disconnected:raise WebSocketDisconnect()
                    await ws.send_json({'kind':'resumed','tick':session.neural.tick})
            async def commands():
                nonlocal disconnected
                try:
                    while True:
                        command=await ws.receive_json()
                        if command=={'kind':'pause'}:gate.clear()
                        elif command=={'kind':'resume'}:gate.set()
                        elif command.get('kind')=='rendered':await acks.put(command)
                        else:raise ValueError('Only pause, resume and motor render acknowledgments are accepted')
                finally:
                    disconnected=True;gate.set();await acks.put(None)
            async def emit(event):
                if '_activity' in event:await ws.send_bytes(event['_activity'])
                await ws.send_json({k:v for k,v in event.items() if k not in ('rates','spikes') and not k.startswith('_')})
                # Physical contact still cannot produce a key until its pose renders.
                if event['kind']=='motor':
                    ack=await asyncio.wait_for(acks.get(),30)
                    if ack!={'kind':'rendered','tick':event['tick']}:raise ValueError('Motor render acknowledgment mismatch')
                    event['render_acknowledged']=True
                    await checkpoint()
            session=Session(target,silenced,bool(config.get('fault')),paced=False,emit=emit,mode=mode)
            live_sessions[session.id]=session
            session.neural.pending=[]
            await session.open();await ws.send_json({'kind':'ready','session':session.id,'tick':0})
            if await ws.receive_json()!={'kind':'start'}:raise ValueError('Expected Start')
            session.checkpoint=checkpoint;receiver=asyncio.create_task(commands())
            await session.run()
    except WebSocketDisconnect:pass
    except Exception as exc:
        try:await ws.send_json({'kind':'error','detail':str(exc)})
        except Exception:pass
    finally:
        if receiver:
            receiver.cancel()
            try:await receiver
            except (asyncio.CancelledError,Exception):pass
        if session:
            session.archive.close();live_sessions.pop(session.id,None)
        if session and hasattr(session,'computer'):
            try:await session.computer.close()
            except Exception:pass
        try:await ws.close()
        except Exception:pass
