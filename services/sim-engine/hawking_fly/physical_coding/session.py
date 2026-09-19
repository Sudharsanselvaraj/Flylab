"""Single-clock session. Policy and privileged evaluation have separate interfaces."""
import asyncio,base64,gzip,hashlib,io,json,time,uuid,zipfile
import numpy as np
from PIL import Image
from .browser import BrowserComputer
from .motor import ComputerActuator,DT,REST
from .policy import NeuralController,ART
from .telemetry import SpikeArchive,packet

class Session:
    def __init__(self,target='Hello World',silenced=(),fault=False,paced=False,emit=None,mode='subgraph'):
        self.mode=mode;self.target=target;self.silenced=list(silenced);self.fault=fault;self.paced=paced;self.emit=emit
        self.id=uuid.uuid4().hex;self.folder=ART/'sessions'/self.id;self.folder.mkdir(parents=True)
        self.records=[];self.decisions=[];self.observations=[];self.controller=NeuralController(silenced,mode)
        self.neural=self.controller.neural;self.neural.pending=[];self.archive=SpikeArchive(self.folder/'spikes.bin');self.neural.spike_sink=self.archive.append;self.checkpoint=None;self.started=None;self.paused_seconds=0;self.neural_wall=0;self.last_pose={'effector':REST,'left_effector':[-.18,1.58,.53],'held':[],'phase':'look','key':None};self.decision=None;self.stopped=False
    async def publish(self,event):
        if self.checkpoint:await self.checkpoint()
        event={'tick':self.neural.tick,'time':round(self.neural.tick*DT,6),**event}
        if self.decision is not None:event['decision_id']=self.decision
        if event['kind']=='motor':self.last_pose=event.copy()
        if event['kind'] in ('motor','browser_input'):
            event['rates']=self.neural.frame()['rates'];event['spikes']=self.neural.recent[-64:]
        if 'rates' in event or event['kind']=='neural':
            elapsed=time.monotonic()-self.started-self.paused_seconds if self.started else 0
            event['metrics']={**self.neural.metrics(),'dt_ms':DT*1000,'real_time_factor':self.neural.tick*DT/elapsed if elapsed>0 else 0,'neural_wall_seconds':self.neural_wall,'mode':'subgraph' if self.mode=='subgraph' else 'full','precision':'float64' if self.mode=='full-precision' else 'float32' if self.mode=='full-fast' else 'float64','graph_sha256':self.neural.g['sha256'],'engine':getattr(self.neural,'engine','SciPy CSR CPU')}
        if 'rates' in event:
            pairs=np.concatenate(self.neural.pending_blocks) if getattr(self.neural,'pending_blocks',[]) else self.neural.pending
            payload=packet(event['tick'],event['rates'],pairs)
            self.neural.pending.clear()
            if hasattr(self.neural,'pending_blocks'):self.neural.pending_blocks.clear()
            if self.mode!='subgraph':
                name=f'activity-{len(self.records):05d}.bin';(self.folder/name).write_bytes(payload)
                event={k:v for k,v in event.items() if k not in ('rates','spikes')};event['activity_file']=name
            event['_activity']=payload
        self.archive.file.flush()
        self.records.append({k:v for k,v in event.items() if not k.startswith('_')})
        if self.emit:await self.emit(event)
        if event.get('render_acknowledged'):self.records[-1]['render_acknowledged']=True
        # Render acknowledgment supplies presentation backpressure; no dramatic delay.
    async def advance(self,n):
        if self.checkpoint:await self.checkpoint()
        start=time.monotonic()
        if self.mode=='subgraph':self.neural.advance(n)
        else:await asyncio.to_thread(self.neural.advance,n)
        self.neural_wall+=time.monotonic()-start
        await self.computer.advance(round(n*DT*1000))
    async def capture(self):
        png=await self.computer.screenshot();sha=hashlib.sha256(png).hexdigest()
        name=f'{len(self.observations):03d}-{self.neural.tick}.png';(self.folder/name).write_bytes(png)
        self.observations.append({'tick':self.neural.tick,'file':name,'sha256':sha})
        await self.publish({'kind':'screen','image':base64.b64encode(png).decode(),'sha256':sha,'file':name})
        return png
    async def open(self):
        self.computer=await BrowserComputer().open(self.target)
        self.actuator=ComputerActuator(self.computer,self.advance,self.publish)
        initial=await self.computer.audit()
        if initial['source']:raise RuntimeError('Editor not empty at initialization')
        self.initial=initial;await self.capture()
    def score(self,png):
        # Privileged evaluator ONLY. Reward never goes into controller.observe.
        a=np.asarray(Image.open(io.BytesIO(png)).convert('RGB'),dtype=float)
        mae=float(np.abs(a[112:532,:400]-a[112:532,800:1200]).mean()/255)
        return {'pixel_mae':mae,'visual_success':mae<.00001,'reward':1-mae}
    async def run(self,max_decisions=48):
        start=time.monotonic();self.started=start;fault_used=False;status='limit';audit=None
        try:
            if not hasattr(self,'computer'):await self.open()
            await self.advance(128)
            await self.publish({'kind':'neural','phase':'warm-up',**self.neural.frame()})
            for i in range(max_decisions):
                if self.stopped:status='stopped';break
                png=await self.capture();self.decision=f'd{i}'
                try:d=await self.controller.observe(png,self.advance,self.publish)
                except ValueError as exc:
                    status='abstained';await self.publish({'kind':'abstention','detail':str(exc)});break
                readout_file=f'readout-{i:03d}.bin';self.controller.last_readout.tofile(self.folder/readout_file);d['readout_file']=readout_file
                d.update({'kind':'decision','id':self.decision,'tick':self.neural.tick});self.decisions.append(d);await self.publish(d)
                if d['mode']=='FINISH':status='finished';break
                if d['mode']=='FOCUS':await self.actuator.focus()
                elif d['mode']=='BACKSPACE':await self.actuator.stroke('Backspace')
                elif d['mode']=='RUN':await self.actuator.stroke('F8')
                elif d['mode']=='TYPE':
                    # Explicit experimental fault at a known decision count,
                    # NEVER repaired here. The next screenshot contains its effect.
                    override='KeyX' if self.fault and not fault_used and i==10 else None
                    if override:fault_used=True;await self.publish({'kind':'fault','intended':d['character'],'physical_key':override})
                    await self.actuator.character(d['character'],override)
                await self.advance(2)
                audit=await self.computer.audit();png=await self.capture()
                await self.publish({'kind':'audit','source':audit['source'],'revision':audit['revision'],'browser_events':audit['events'],'preview_hash':hashlib.sha256(png).hexdigest(),'score':self.score(png)})
            audit=await self.computer.audit();png=await self.capture()
            score=self.score(png)
            self.result={**score,'success':status=='finished' and score['visual_success'] and audit['runs']>0,'status':status,'decisions':len(self.decisions),'keystrokes':sum(e.get('type')=='keydown' for e in audit['events']),'corrections':sum(d['mode']=='BACKSPACE' for d in self.decisions),'revision':audit['revision'],'ticks':self.neural.tick,'wall_seconds':time.monotonic()-start,'fault_injected':fault_used,'all_inputs_trusted':all(e['trusted'] for e in audit['events']),'source':audit['source'],'engine':getattr(self.neural,'engine','SciPy CSR CPU'),'mode':self.mode,'checkpoint_sha256':self.controller.sha,'graph_sha256':self.neural.g['sha256'],'target':self.target,'silenced':self.silenced}
            await self.publish({'kind':'neural','phase':'final',**self.neural.frame()})
            await self.publish({'kind':'result','session':self.id,**self.result})
            return self.result
        finally:
            if hasattr(self,'computer'):
                if audit is None:audit=await self.computer.audit()
                await self.save(audit);await self.computer.close()
    async def save(self,audit):
        self.archive.close()
        meta={'version':2,'mode':self.mode,'spike_archive':{'file':'spikes.bin','format':'little-endian uint32 pairs (tick, neuron index)','events':self.archive.count,'neurons':[n['body_id'] for n in self.neural.nodes],'sha256':hashlib.sha256((self.folder/'spikes.bin').read_bytes()).hexdigest()},'id':self.id,'dt':DT,'initial':getattr(self,'initial',{}),'result':getattr(self,'result',None),'decisions':self.decisions,'observations':self.observations}
        (self.folder/'episode.json').write_text(json.dumps(meta,separators=(',',':')))
        # Screens stored separately; replay reads exact frames, never redraws source.
        records=[{k:v for k,v in e.items() if k!='image'} for e in self.records]
        with gzip.open(self.folder/'timeline.json.gz','wt') as f:json.dump(records,f,separators=(',',':'))
        (self.folder/'index.html').write_text(audit['source'])
        with zipfile.ZipFile(self.folder/'project.zip','w') as z:
            z.writestr('index.html',audit['source']);z.writestr('style.css','');z.writestr('script.js','')
