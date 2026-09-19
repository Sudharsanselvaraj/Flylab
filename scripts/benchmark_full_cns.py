"""Actual local sparse-rate benchmark, not a claimed biological fidelity test."""
import json,time,platform,resource
from pathlib import Path
import numpy as np
from scipy.sparse import load_npz
root=Path(__file__).resolve().parents[1];cache=root/'data/full_cns';out=root/'experiments/full_cns';out.mkdir(exist_ok=True,parents=True)
w=load_npz(cache/'normalized.npz');n=w.shape[0];rng=np.random.default_rng(614);r=np.zeros(n,np.float32);bias=rng.normal(0,.18,n).astype(np.float32)
for _ in range(5):r=.35*r+.65*np.tanh(.85*(w@r)+bias)
rows=[]
for dtype in (np.float32,np.float64):
 matrix=w.astype(dtype);state=r.astype(dtype);t=time.perf_counter()
 for _ in range(100):state=.35*state+.65*np.tanh(.85*(matrix@state)+bias)
 elapsed=time.perf_counter()-t;rows.append({'engine':'scipy CSR CPU','dtype':str(np.dtype(dtype)),'ticks':100,'dt_ms':2,'wall_seconds':elapsed,'real_time_factor':.2/elapsed,'finite':bool(np.isfinite(state).all())})
import torch
try:
 if torch.backends.mps.is_available():
  # Probe native sparse support, do not silently densify a 176k² graph.
  x=torch.sparse_csr_tensor(torch.tensor(w.indptr[:3]),torch.tensor(w.indices[:w.indptr[2]]),torch.tensor(w.data[:w.indptr[2]]),size=(2,n),device='mps')
  torch.mv(x,torch.ones(n,device='mps'));gpu='Sparse CSR probe supported; full benchmark pending'
 else:gpu='No MPS device available'
except Exception as e:gpu=str(e).split('\n')[0][:400]
result={'manifest':json.loads((cache/'manifest.json').read_text()),'platform':platform.platform(),'cpu':platform.processor(),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'benchmarks':rows,'gpu_sparse_probe':gpu,'event_driven':'Not equivalent to this continuous rate model: all nonzero rates contribute each tick. No events-only speedup claimed.'}
(out/'benchmark.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
