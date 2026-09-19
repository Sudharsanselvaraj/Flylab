"""Pixel-only learned visual transducer. No HTML literals or task IDs in inference.

Engineered sensor: fixed glyph windows in a monospace, single-line workspace.
Trained: neural glyph readout, positional copy/literal transducer, editing gate.
Generic comparison features are explicit; they are not a general coding skill.
"""
import hashlib
from collections import deque
from pathlib import Path
import numpy as np
from hawking_fly.coding.core import Reservoir,ROOT,graph
from .browser import retinal_patches
from .motor import DT

ART=ROOT/'experiments/physical_coding'
ALPHABET=''.join(chr(i) for i in range(32,127))
MODES=['FOCUS','BACKSPACE','TYPE','RUN','FINISH']

class NeuralState(Reservoir):
    def __init__(self,silenced=()):
        super().__init__();self.r=np.zeros(len(self.nodes));self.phase=np.zeros(len(self.nodes));self.drive=np.zeros(len(self.nodes))
        self.blocked=np.array([i for i,n in enumerate(self.nodes) if n['body_id'] in silenced],int)
        self.tick=0;self.recent=[];self.pending=None;self.spike_sink=None;self.total_spikes=0;self.window=deque()
    def stimulus(self,patch):
        self.drive[:]=0;self.drive[self.inputs]=self.projection@patch
    def advance(self,n):
        for _ in range(n):
            self.tick+=1;self.r=.35*self.r+.65*np.tanh(self.drive+.85*(self.w@self.r)+self.bias)
            self.r[self.blocked]=0
            self.phase+=np.maximum(self.r,0)*70*DT
            fired=np.flatnonzero(self.phase>=1);self.phase[fired]-=1
            events=[{'id':f'n{self.tick}:{int(i)}','tick':self.tick,'neuron':int(i)} for i in fired]
            self.recent.extend(events)
            if self.pending is not None:self.pending.extend(events)
            self.total_spikes+=len(fired)
            self.window.append((self.tick,len(fired)))
            while self.window and self.window[0][0]<=self.tick-500:self.window.popleft()
            if self.spike_sink:self.spike_sink(self.tick,fired)
        self.recent=self.recent[-2048:]
        return self.r[self.read_indices].copy()
    def metrics(self):return {'simulated':len(self.nodes),'active':int(np.count_nonzero(self.r>1/70)),'active_threshold_hz':1,'spikes_total':self.total_spikes,'spikes_per_second':sum(n for _,n in self.window)/max(DT,min(1,self.tick*DT))}
    def frame(self):return {'rates':(np.maximum(self.r,0)*70).round(4).tolist(),'spikes':self.recent[-256:]}

def mlp(data,prefix,x):
    h=np.maximum(0,np.asarray(x)@data[prefix+'_w1']+data[prefix+'_b1'])
    return h@data[prefix+'_w2']+data[prefix+'_b2']

class NeuralController:
    def __init__(self,silenced=(),mode='subgraph'):
        path=ART/('policy.npz' if mode=='subgraph' else 'full_network/policy.npz')
        if not path.exists():raise ValueError('No physical-key checkpoint. Run scripts/train_physical_coding.py first.')
        self.visual_cache={};self.data=dict(np.load(path,allow_pickle=False));self.sha=hashlib.sha256(path.read_bytes()).hexdigest()
        if mode=='subgraph':self.neural=NeuralState(silenced)
        else:
            from .full_network import FullNeuralState
            self.neural=FullNeuralState(silenced,precision='float64' if mode=='full-precision' else 'float32')
        if str(self.data['graph_sha'])!=self.neural.g['sha256']:raise ValueError('Policy graph mismatch')
    async def observe(self,png,advance,publish):
        # No audit, source, DOM, reward, task identity or source length argument.
        patches,focused,ran,caret=retinal_patches(png)
        readings=[];readouts=[];sample_ticks=[];refreshed=[]
        for i,patch in enumerate(patches):
            # Pixel-exact sensory memory: only unchanged retinal cells may reuse
            # their previously measured glyph/readout. All neural states continue
            # integrating during new sensory dwell and physical movement.
            digest=hashlib.sha256(patch.tobytes()).hexdigest()
            cached=self.visual_cache.get(i)
            if cached is None or cached[0]!=digest:
                self.neural.stimulus(patch);await advance(16)
                state=(self.neural.r[self.neural.read_indices]-self.data['mean'])/self.data['scale']
                cached=(digest,ALPHABET[int(np.argmax(mlp(self.data,'glyph',state)))],self.neural.r[self.neural.read_indices].astype('<f4').copy(),self.neural.tick)
                self.visual_cache[i]=cached;refreshed.append(i)
            readings.append(cached[1]);readouts.append(cached[2]);sample_ticks.append(cached[3])
            if i%8==7 and refreshed and refreshed[-1]>i-8:await publish({'kind':'neural','phase':'look','retinal_slot':i,**self.neural.frame()})
        self.last_readout=np.asarray(readouts,dtype='<f4')
        target=''.join(readings[:24]).rstrip()
        observed=''.join(readings[24:56]).rstrip()
        # Native red caret pixels retain meaningful trailing spaces.
        if focused and caret is not None:observed=''.join(readings[24:56])[:max(0,caret)]
        preview=''.join(readings[56:80]).rstrip()
        length=len(target)
        if not 1<=length<=20:raise ValueError('Visual text is outside the trained 1–20 glyph envelope')
        # The learned transducer predicts copy locations/literals for each output
        # position. No source template, grammar rule or solution is stored here.
        planned=[]
        for pos in range(32):
            x=np.zeros(53);x[length]=1;x[21+pos]=1
            label=int(np.argmax(mlp(self.data,'transducer',x)))
            if label==119:break
            planned.append(target[label] if label<24 and label<len(target) else ALPHABET[label-24] if label>=24 else ' ')
        proposal=''.join(planned)
        features=np.array([float(not proposal.startswith(observed)),float(len(observed)<len(proposal)),float(focused),float(ran),float(preview==target)])
        mode=MODES[int(np.argmax(mlp(self.data,'gate',features)))]
        char=proposal[len(observed)] if mode=='TYPE' and len(observed)<len(proposal) else None
        if mode=='TYPE' and char is None:raise ValueError('Learned policy produced an invalid character position')
        return {'mode':mode,'character':char,'visual_reading':{'target':target,'editor':observed,'preview':preview,'caret':caret},'features':features.tolist(),'neural_event_ids':[e['id'] for e in self.neural.recent[-32:]],'observation_sha256':hashlib.sha256(png).hexdigest(),'readout_sha256':hashlib.sha256(self.last_readout.tobytes()).hexdigest(),'readout_indices':self.neural.read_indices.tolist(),'readout_shape':list(self.last_readout.shape),'retinal_refreshed_slots':refreshed,'readout_sample_ticks':sample_ticks}
