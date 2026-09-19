"""Pixel-only connectome reservoir and compact learned readout.

No source, DOM, task identifiers, reward or teacher labels enter infer().
Rate propagation is modeled; threshold-integrated spike markers are recorded,
not represented as experimentally validated spike trains.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np
from scipy.sparse import csr_matrix

ROOT=Path(__file__).resolve().parents[4]
ART=ROOT/'experiments/coding_fly'
VERSION='coding-colour-v1'
DT=.02
STEPS=16
PALETTE=['#315cba','#b04f43','#377b61']
ELEMENTS=['heading','button','cards']
TOKENS=['<h1>Hello, world</h1>','<button>Get started</button>','<section><article>One</article><article>Two</article><article>Three</article></section>']
SELECTORS=['h1','button','article']
ACTIONS=[{'name':'Insert '+e,'token':t} for e,t in zip(ELEMENTS,TOKENS)]+[{'name':f'Colour {e} {c+1}','token':f'<style>{sel}{{background:{colour}}}</style>'} for e,sel in zip(ELEMENTS,SELECTORS) for c,colour in enumerate(PALETTE)]+[{'name':'Finish','token':None}]
BASE='<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#faf8f4;font:14px Arial;color:white}h1,button,section{position:absolute;box-sizing:border-box;margin:0}h1{left:12px;top:12px;width:216px;height:40px;padding:10px;font-size:17px;background:#777}button{left:12px;top:68px;width:120px;height:32px;border:0;border-radius:4px;color:white;background:#777}section{left:12px;top:116px;width:216px;height:50px;display:flex;gap:6px}article{flex:1;background:#777;padding:12px 4px;border-radius:4px;text-align:center}</style></head><body>\n'

def source_for(state):
    # Privileged task generator only, never called by inference.
    return BASE+''.join(TOKENS[i]+(ACTIONS[3+i*3+s-2]['token'] if s>=2 else '') for i,s in enumerate(state) if s)

def split(target):
    value=sum((i+1)*x for i,x in enumerate(target))%5
    return 'test' if value==0 else 'validation' if value==1 else 'train'

def teacher(target,current):
    # Offline imitation oracle. The trained controller never calls this.
    for i,(a,b) in enumerate(zip(target,current)):
        if b==0:return i
        if a!=b:return 3+i*3+a-2
    return 12

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def graph():
    g=json.loads((ART/'graph.json').read_text())
    payload={k:v for k,v in g.items() if k!='sha256'}
    if hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()!=g['sha256']:
        raise ValueError('Graph content hash mismatch')
    return g

def pixels_to_features(pixels):
    p=np.asarray(pixels,dtype=np.float64)
    if p.shape!=(24*32*3,) or not np.all(np.isfinite(p)) or np.min(p)<0 or np.max(p)>255:
        raise ValueError('Expected 32×24 RGB viewport pixels, bytes only')
    # Fixed spatial pooling over target + actual preview. No OCR or DOM access.
    p=p.reshape(24,32,3)/255
    return p.reshape(6,4,8,4,3).mean(axis=(1,3)).reshape(-1)*2-1

class Reservoir:
    def __init__(self,g=None):
        self.g=g or graph();self.nodes=self.g['nodes'];n=len(self.nodes)
        ids={node['body_id']:i for i,node in enumerate(self.nodes)}
        pre=np.array([ids[str(e['pre'])] for e in self.g['edges']]);post=np.array([ids[str(e['post'])] for e in self.g['edges']]);w=np.array([e['weight'] for e in self.g['edges']],float)
        total=np.bincount(post,weights=w,minlength=n)
        self.w=csr_matrix((w/np.maximum(total[post],1),(post,pre)),shape=(n,n))
        rng=np.random.default_rng(614)
        self.inputs=np.array([i for i,v in enumerate(self.nodes) if v['input']])
        self.projection=rng.normal(0,.32,(len(self.inputs),144))
        self.bias=rng.normal(0,.18,n)
        self.read_indices=np.array([i for i,v in enumerate(self.nodes) if not v['input']])
    def encode(self,pixels,silenced=(),start_tick=0,trace=False):
        x=pixels_to_features(pixels)
        n=len(self.nodes);r=np.zeros(n);phase=np.zeros(n);drive=np.zeros(n)
        drive[self.inputs]=self.projection@x
        blocked=np.array([i for i,node in enumerate(self.nodes) if node['body_id'] in silenced],dtype=int)
        events=[];trajectory=[]
        # Defined stimulus-locked response windows, reset on each observation.
        # No hidden task phase / source / previous oracle state.
        for step in range(STEPS):
            r=.35*r+.65*np.tanh(drive+.85*(self.w@r)+self.bias)
            r[blocked]=0
            hz=np.maximum(r,0)*70;phase+=hz*DT
            counts=np.floor(phase).astype(int);fired=np.flatnonzero(counts);phase-=counts
            if trace:
                tick=start_tick+step+1
                events.extend({'tick':tick,'neuron':int(i)} for i in fired for _ in range(counts[i]))
                trajectory.append({'tick':tick,'rates':hz.round(4).tolist()})
        return r[self.read_indices].astype(np.float32),{'rates':(np.maximum(r,0)*70).round(4).tolist(),'spikes':events,'trajectory':trajectory}

class Policy:
    def __init__(self,path=None):
        self.path=path or ART/'trained_policy/policy.npz'
        self.g=graph();self.reservoir=Reservoir(self.g)
        if not self.path.exists():raise ValueError('No trained checkpoint. Capture browser curriculum and train first.')
        with np.load(self.path,allow_pickle=False) as p:
            if str(p['graph_sha'])!=self.g['sha256'] or str(p['version'])!=VERSION:raise ValueError('Checkpoint graph/version mismatch')
            self.mean=p['mean'];self.scale=p['scale'];self.w1=p['w1'];self.b1=p['b1'];self.w2=p['w2'];self.b2=p['b2']
        n=len(self.reservoir.read_indices)
        if self.w1.shape!=(n,48) or self.w2.shape!=(48,13) or self.mean.shape!=(n,) or self.scale.shape!=(n,) or self.b1.shape!=(48,) or self.b2.shape!=(13,):raise ValueError('Checkpoint shape mismatch')
        if not all(np.isfinite(a).all() for a in (self.mean,self.scale,self.w1,self.w2,self.b1,self.b2)) or np.any(self.scale<=0):raise ValueError('Invalid checkpoint values')
        self.sha=hashlib.sha256(self.path.read_bytes()).hexdigest()
    def infer(self,pixels,silenced=(),tick=0):
        x,neural=self.reservoir.encode(pixels,silenced,tick,True)
        h=np.tanh((x-self.mean)/self.scale@self.w1+self.b1)
        logits=h@self.w2+self.b2
        return int(np.argmax(logits)),neural,logits.tolist()
