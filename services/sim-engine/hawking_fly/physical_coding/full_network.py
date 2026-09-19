"""Every cached MaleCNS Neuron and every published edge between them.

This is an engineered positive-weight rate model, not validated physiology.
The 576 readout sites and 101 visual input sites retain their measured identities;
all 176,422 state variables participate in recurrent propagation every tick.
"""
import hashlib,json
from collections import deque
from functools import lru_cache
import numpy as np
from scipy.sparse import load_npz
from hawking_fly.coding.core import ROOT,Reservoir
from .motor import DT

CACHE=ROOT/'data/full_cns'
@lru_cache(maxsize=1)
def topology():
    meta=json.loads((CACHE/'manifest.json').read_text());ids=np.load(CACHE/'body_ids.npy');w=load_npz(CACHE/'normalized.npz')
    if hashlib.sha256(w.indptr.tobytes()+w.indices.tobytes()+w.data.tobytes()).hexdigest()!=meta['csr_sha256']:raise ValueError('Full CNS connectivity hash mismatch')
    return meta,ids,w

class FullNeuralState:
    def __init__(self,silenced=(),precision='float32'):
        meta,ids,w=topology();small=Reservoir();self.w=w.astype(precision,copy=False);self.ids=ids;self.engine='SciPy CSR CPU';self.matvec=lambda x:self.w@x
        if precision=='float32':
            try:
                from .native_csr import NativeCSR
                self.matvec=NativeCSR(self.w);self.engine='Parallel GCD CSR CPU'
            except (FileNotFoundError,OSError,ValueError,AssertionError):pass
        self.g={'sha256':meta['csr_sha256']};self.mode='full';self.tick=0;self.recent=[];self.pending=None;self.pending_blocks=[];self.spike_sink=None;self.total_spikes=0;self.window=deque()
        lookup={str(v):i for i,v in enumerate(ids)};self.nodes=[{'body_id':str(v)} for v in ids]
        self.inputs=np.array([lookup[small.nodes[i]['body_id']] for i in small.inputs]);self.read_indices=np.array([lookup[small.nodes[i]['body_id']] for i in small.read_indices]);self.projection=small.projection.astype(precision)
        self.r=np.zeros(len(ids),precision);self.phase=np.zeros(len(ids),precision);self.drive=np.zeros(len(ids),precision)
        self.bias=np.random.default_rng(614).normal(0,.18,len(ids)).astype(precision)
        self.readout_mask=np.zeros(len(ids),bool);self.readout_mask[self.read_indices]=True
        self.blocked=np.array([lookup[v] for v in silenced],int)
    def stimulus(self,patch):self.drive.fill(0);self.drive[self.inputs]=self.projection@patch
    def advance(self,n):
        recent=[]
        for _ in range(n):
            self.tick+=1;self.r=.35*self.r+.65*np.tanh(self.drive+.85*(self.matvec(self.r))+self.bias);self.r[self.blocked]=0
            self.phase+=np.maximum(self.r,0)*70*DT;fired=np.flatnonzero(self.phase>=1);self.phase[fired]-=1
            self.total_spikes+=len(fired);self.window.append((self.tick,len(fired)))
            while self.window and self.window[0][0]<=self.tick-500:self.window.popleft()
            if self.spike_sink:self.spike_sink(self.tick,fired)
            if self.pending is not None:
                pairs=np.empty((len(fired),2),'<u4');pairs[:,0]=self.tick;pairs[:,1]=fired;self.pending_blocks.append(pairs)
            # Recent detail window only. Full untruncated events go to the archive.
            recent.extend({'id':f'n{self.tick}:{int(i)}','tick':self.tick,'neuron':int(i)} for i in fired[self.readout_mask[fired]])
        self.recent=(self.recent+recent)[-2048:]
        return self.r[self.read_indices].copy()
    def metrics(self):return {'simulated':len(self.nodes),'active':int(np.count_nonzero(self.r>1/70)),'active_threshold_hz':1,'spikes_total':self.total_spikes,'spikes_per_second':sum(n for _,n in self.window)/max(DT,min(1,self.tick*DT))}
    def frame(self):return {'rates':(np.maximum(self.r,0)*70).astype('<f4'),'spikes':self.recent[-256:]}
