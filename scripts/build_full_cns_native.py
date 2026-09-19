"""Compile and verify the optional macOS GCD sparse kernel against SciPy."""
import ctypes,hashlib,json,platform,subprocess,sys,time
from pathlib import Path
import numpy as np
from scipy.sparse import load_npz
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'data/full_cns';SOURCE=ROOT/'services/sim-engine/hawking_fly/physical_coding/csr_parallel.c'
if platform.system()!='Darwin':raise SystemExit('Native GCD kernel is macOS-only; use the portable SciPy runtime.')
subprocess.run(['clang','-O3','-ffp-contract=fast','-dynamiclib',str(SOURCE),'-o',str(CACHE/'csr_parallel_fma.dylib')],check=True)
meta={'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'compiler':'clang -O3 -ffp-contract=fast','platform':platform.platform()}
# Temporary manifest permits loading for this verification; runtime checks success.
(CACHE/'native.json').write_text(json.dumps(meta));sys.path.insert(0,str(ROOT/'services/sim-engine'))
from hawking_fly.physical_coding.native_csr import NativeCSR
w=load_npz(CACHE/'normalized.npz');native=NativeCSR(w,require_verified=False);rng=np.random.default_rng(29);a=np.zeros(w.shape[0],np.float32);b=a.copy();pa=a.copy();pb=a.copy();bias=rng.normal(0,.18,len(a)).astype(np.float32);start=time.perf_counter()
for i in range(256):
 drive=np.zeros_like(a);drive[:101]=np.sin(i*.13+np.arange(101))
 a=.35*a+.65*np.tanh(drive+.85*(w@a)+bias)
 b=.35*b+.65*np.tanh(drive+.85*native(b)+bias)
 pa+=np.maximum(a,0)*70*.002;pb+=np.maximum(b,0)*70*.002
 assert np.array_equal(a,b),f'Rate trajectory diverged at tick {i}'
 assert np.array_equal(pa>=1,pb>=1),f'Threshold events diverged at tick {i}'
 pa[pa>=1]-=1;pb[pb>=1]-=1
meta.update(verified=True,trajectory_ticks=256,bitwise_rates=True,bitwise_threshold_events=True,verification_wall_seconds=time.perf_counter()-start)
for name,fn in [('scipy',lambda x:w@x),('gcd',native)]:
 start=time.perf_counter()
 for _ in range(100):fn(a)
 meta[name+'_matvec_seconds_per_tick']=(time.perf_counter()-start)/100
(CACHE/'native.json').write_text(json.dumps(meta,indent=2));(ROOT/'experiments/full_cns/native_verification.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
