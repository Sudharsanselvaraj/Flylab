"""Train a separate readout on actual full-network trajectories and real glyph pixels.

The already-trained syntax transducer/edit gate are retained; the glyph readout,
normalization and graph hash are replaced. No runtime teacher or source injection.
"""
import sys,time,json,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services/sim-engine'))
from hawking_fly.physical_coding.full_network import FullNeuralState
from hawking_fly.physical_coding.policy import ART
import train_physical_coding as training
OUT=Path(sys.argv[sys.argv.index('--output')+1]) if '--output' in sys.argv else ART/'full_network';OUT.mkdir(exist_ok=True,parents=True);training.ART=OUT
resume='--resume' in sys.argv
neural=FullNeuralState();start=time.monotonic()
if resume:
 saved=np.load(OUT/'features.npz');x=saved['x'];y=saved['y'];mean=saved['mean'];scale=saved['scale'];training_ticks=int(saved['ticks'])
 print(json.dumps({'phase':'resume saved full-network features','ticks':training_ticks}),flush=True)
else:
 rng=np.random.default_rng(37);data=np.load(ART/'glyph_captures.npz');x=[];y=[]
 for repeat in range(4):
  for step,i in enumerate(rng.permutation(len(data['labels']))):
   neural.stimulus(np.clip(data['patches'][i]+rng.normal(0,.005,144),-1,1));x.append(neural.advance(16));y.append(data['labels'][i])
   if step%32==31:print(json.dumps({'phase':'full-network feature capture','repeat':repeat+1,'glyphs':step+1,'ticks':neural.tick,'wall_seconds':time.monotonic()-start}),flush=True)
  print(json.dumps({'phase':'full-network feature capture','repeat':repeat+1,'ticks':neural.tick,'wall_seconds':time.monotonic()-start}),flush=True)
 x=np.array(x);mean=x.mean(0);scale=np.maximum(x.std(0),.00005);x=(x-mean)/scale;training_ticks=neural.tick
 np.savez_compressed(OUT/'features.npz',x=x,y=y,mean=mean,scale=scale,ticks=training_ticks)
model,history=training.optimize('full_cns_glyph_readout',x,y,95,1000,resume=resume)
out=dict(np.load(ART/'policy.npz',allow_pickle=False));out.update(mean=mean,scale=scale,graph_sha=neural.g['sha256']);training.export('glyph',model,out);np.savez_compressed(OUT/'policy.npz',**out)
manifest={'version':'full-cns-heading-v1','scope':'Full positive-weight recurrent graph; 101 engineered visual inputs and 576 learned readout sites. Same narrow heading grammar. No biophysical validity claim.','graph_sha256':neural.g['sha256'],'checkpoint_sha256':hashlib.sha256((OUT/'policy.npz').read_bytes()).hexdigest(),'inherited_transducer_gate_checkpoint':hashlib.sha256((ART/'policy.npz').read_bytes()).hexdigest(),'neurons':len(neural.nodes),'resumed':resume,'training_ticks':training_ticks,'training_wall_seconds':time.monotonic()-start,'history':history,'trainable_parameters':sum(p.numel() for p in model.parameters()),'live_evaluation':None}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest),flush=True)
