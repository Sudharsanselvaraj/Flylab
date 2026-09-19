"""Optional macOS parallel CSR; no topology or time-step approximation."""
import ctypes,hashlib,json,platform
from pathlib import Path
import numpy as np
from hawking_fly.coding.core import ROOT
CACHE=ROOT/'data/full_cns'
class NativeCSR:
    def __init__(self,w,require_verified=True):
        source=Path(__file__).with_name('csr_parallel.c');meta=json.loads((CACHE/'native.json').read_text())
        if require_verified and not meta.get('verified'):raise ValueError('Native kernel has not passed trajectory verification')
        if platform.system()!='Darwin' or meta['source_sha256']!=hashlib.sha256(source.read_bytes()).hexdigest():raise ValueError('Native build unavailable or stale')
        self.lib=ctypes.CDLL(str(CACHE/'csr_parallel_fma.dylib'));self.fn=self.lib.csr_matvec;self.fn.argtypes=[ctypes.c_void_p]*5+[ctypes.c_size_t]*2;self.fn.restype=None
        assert w.data.dtype==np.float32 and w.indices.dtype==np.int32 and w.indptr.dtype==np.int32
        self.w=w;self.out=np.empty(w.shape[0],np.float32)
    def __call__(self,x):
        assert x.dtype==np.float32 and x.flags.c_contiguous
        self.fn(self.w.indptr.ctypes.data,self.w.indices.ctypes.data,self.w.data.ctypes.data,x.ctypes.data,self.out.ctypes.data,len(x),256)
        return self.out
