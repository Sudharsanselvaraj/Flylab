"""Offline supervised curriculum. Privileged HTML teacher is confined here.

This learns a narrow heading transducer, not arbitrary coding. Runtime only
receives screen pixels; all live edits use the contact-gated Chromium actuator.
"""
import asyncio,hashlib,itertools,json,sys,time,gzip
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services/sim-engine'))
import numpy as np
import torch
from torch import nn
from hawking_fly.physical_coding.browser import BrowserComputer,retinal_patches
from hawking_fly.physical_coding.policy import ART,ALPHABET,NeuralState

torch.set_num_threads(2);torch.manual_seed(37)

async def capture():
    ART.mkdir(parents=True,exist_ok=True);samples=[];labels=[]
    # Browser-rendered glyphs; initialized fixtures are never a live episode.
    for start in range(0,len(ALPHABET),20):
        chars=ALPHABET[start:start+20]
        c=await BrowserComputer().open(chars,starter=chars,training=True)
        try:
            png=await c.screenshot();(ART/f'glyphs-{start}.png').write_bytes(png)
            p,*_=retinal_patches(png)
            for offset in (0,24):
                for i,ch in enumerate(chars):samples.append(p[offset+i]);labels.append(ALPHABET.index(ch))
        finally:await c.close()
    np.savez_compressed(ART/'glyph_captures.npz',patches=samples,labels=labels)

class MLP(nn.Sequential):
    def __init__(self,n,h,k):super().__init__(nn.Linear(n,h),nn.ReLU(),nn.Linear(h,k))

def optimize(name,x,y,nclasses,epochs,hidden=128,resume=False):
    model=MLP(x.shape[1],hidden,nclasses);opt=torch.optim.Adam(model.parameters(),lr=.008)
    X=torch.tensor(x,dtype=torch.float32);Y=torch.tensor(y,dtype=torch.long);history=[]
    checkpoint=ART/(name+'-optimizer.pt');start=0
    dataset_sha=hashlib.sha256(X.numpy().tobytes()+Y.numpy().tobytes()).hexdigest()
    if resume:
        saved=torch.load(checkpoint,weights_only=False)
        if saved['dataset_sha256']!=dataset_sha:raise ValueError('Resume dataset differs')
        model.load_state_dict(saved['model']);opt.load_state_dict(saved['optimizer']);start=saved['epoch'];history=saved['history'];epochs=start+100
    before=hashlib.sha256(b''.join(p.detach().numpy().tobytes() for p in model.parameters())).hexdigest()
    for step in range(start,epochs):
        pred=model(X);loss=nn.functional.cross_entropy(pred,Y)
        opt.zero_grad();loss.backward();opt.step()
        if step%100==0 or step==epochs-1:
            row={'component':name,'epoch':step+1,'loss':float(loss.detach()),'offline_accuracy':float((pred.argmax(1)==Y).float().mean())};history.append(row)
            print(json.dumps(row),flush=True)
            torch.save({'model':model.state_dict(),'optimizer':opt.state_dict(),'epoch':step+1,'history':history,'dataset_sha256':dataset_sha,'initial_parameter_sha256':before,'final_parameter_sha256':hashlib.sha256(b''.join(p.detach().numpy().tobytes() for p in model.parameters())).hexdigest()},checkpoint)
    return model,history

def export(prefix,model,out):
    out.update({prefix+'_w1':model[0].weight.detach().numpy().T,prefix+'_b1':model[0].bias.detach().numpy(),prefix+'_w2':model[2].weight.detach().numpy().T,prefix+'_b2':model[2].bias.detach().numpy()})

def train(resume=False):
    data=dict(np.load(ART/'glyph_captures.npz'));episodes_path=ART/'training_episodes.json'
    episode_rows=json.loads(episodes_path.read_text()) if episodes_path.exists() else []
    patches=list(data['patches']);labels=list(data['labels'])
    for ep in episode_rows:
        folder=ART/'sessions'/ep['session'];meta=json.loads((folder/'episode.json').read_text())
        with gzip.open(folder/'timeline.json.gz','rt') as f:timeline=json.load(f)
        audits=[e for e in timeline if e['kind']=='audit']
        for obs in meta['observations'][::8]:
            state=next((e['source'] for e in reversed(audits) if e['tick']<=obs['tick']),'')
            retinal,*_=retinal_patches((folder/obs['file']).read_bytes())
            for offset,text,width in [(0,ep['target'],24),(24,state,32)]:
                for i,ch in enumerate(text.ljust(width)[:width]):patches.append(retinal[offset+i]);labels.append(ALPHABET.index(ch))
    data={'patches':np.array(patches),'labels':np.array(labels)}
    rng=np.random.default_rng(37);neural=NeuralState();x=[];y=[]
    for repeat in range(8):
        for i in rng.permutation(len(data['labels'])):
            patch=np.clip(data['patches'][i]+rng.normal(0,.005,144),-1,1)
            neural.stimulus(patch);x.append(neural.advance(16));y.append(data['labels'][i])
    x=np.array(x);mean=x.mean(0);scale=np.maximum(x.std(0),.005);x=(x-mean)/scale
    glyph,history=optimize('neural_glyph_readout',x,y,95,600,resume=resume)
    # Train a generic positional copy/literal transducer from paired examples.
    # Every supported length appears in training; WORDS are held out in testing.
    tx=[];ty=[]
    for length in range(1,21):
        for pos in range(32):
            features=np.zeros(53);features[length]=1;features[21+pos]=1
            # Privileged training syntax, absent from inference module.
            prefix='<h1>';suffix='</h1>'
            if pos<4:label=24+ALPHABET.index(prefix[pos])
            elif pos<4+length:label=pos-4
            elif pos<9+length:label=24+ALPHABET.index(suffix[pos-4-length])
            else:label=119
            tx.append(features);ty.append(label)
    transducer,h=optimize('heading_transducer',np.array(tx),ty,120,1600,resume=resume);history+=h
    gx=[];gy=[]
    for wrong,incomplete,focused,ran,match in itertools.product((0,1),repeat=5):
        if not wrong and not incomplete:
            mode=4 if ran and match else 3
        elif not focused:mode=0
        elif wrong:mode=1
        else:mode=2
        gx.append([wrong,incomplete,focused,ran,match]);gy.append(mode)
    gate,h=optimize('generic_edit_gate',np.array(gx),gy,5,500,16,resume=resume);history+=h
    out={'mean':mean,'scale':scale,'graph_sha':neural.g['sha256']}
    for name,m in [('glyph',glyph),('transducer',transducer),('gate',gate)]:export(name,m,out)
    np.savez_compressed(ART/'policy.npz',**out)
    torch.save({'glyph':glyph.state_dict(),'transducer':transducer.state_dict(),'gate':gate.state_dict(),'seed':37},ART/'training_checkpoint.pt')
    manifest={'version':'physical-heading-v1','seed':37,'graph_sha256':neural.g['sha256'],'checkpoint_sha256':hashlib.sha256((ART/'policy.npz').read_bytes()).hexdigest(),'trainable_parameters':sum(p.numel() for m in [glyph,transducer,gate] for p in m.parameters()),'curriculum':'Chromium glyph fixtures; all heading lengths 1–20; generic editing-state combinations','scope':'Single-line heading only. Fixed monospace retinal windows. No general code synthesis. Word recombination is the held-out test.','history':history,'training_episodes':episode_rows,'split':{'train':['Learn Keys','Neural Lab','Blue Sky'],'validation':['Green Lab'],'test':['Hello Fly','Fly World'],'acceptance':['Hello World']},'live_episode_results':None}
    (ART/'manifest.json').write_text(json.dumps(manifest,indent=2))

async def collect_episodes():
    from hawking_fly.physical_coding.session import Session
    rows=[]
    for target in ['Learn Keys','Neural Lab','Blue Sky']:
        session=Session(target,fault=target=='Blue Sky');result=await session.run()
        rows.append({'session':session.id,**result});print(json.dumps(rows[-1]),flush=True)
    (ART/'training_episodes.json').write_text(json.dumps(rows,indent=2))

if __name__=='__main__':
    if not (ART/'glyph_captures.npz').exists():asyncio.run(capture())
    if '--episodes' in sys.argv:asyncio.run(collect_episodes())
    train(resume='--resume' in sys.argv)
