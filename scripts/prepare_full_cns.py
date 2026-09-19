"""Filter the published segment graph to every cached neuPrint Neuron ID.

No weight/degree/region threshold. Preserve every positive Neuron→Neuron edge.
The original file includes non-neuron fragments, excluded explicitly here.
"""
import hashlib,json,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
from scipy.sparse import coo_matrix,save_npz
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/full_cns';OUT.mkdir(exist_ok=True,parents=True)
ids=np.sort(pd.read_parquet(ROOT/'data/anatomy/neurons.parquet',columns=['bodyId']).bodyId.to_numpy(dtype=np.int64))
source=OUT/'weights.feather'
if not source.exists():
 from urllib.request import urlopen
 url='https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/connectome-weights-male-cns-v1.0-minconf-0.5.feather'
 temp=OUT/'weights.feather.part'
 with urlopen(url,timeout=60) as response,temp.open('wb') as output:
  for block in iter(lambda:response.read(8*1024*1024),b''):output.write(block)
 temp.replace(source)
reader=pa.ipc.open_file(pa.memory_map(str(source)));pres=[];posts=[];weights=[];total=0;start=time.monotonic()
for i in range(reader.num_record_batches):
 b=reader.get_batch(i);pre=b.column(0).to_numpy();post=b.column(1).to_numpy();w=b.column(2).to_numpy();total+=len(w)
 a=np.searchsorted(ids,pre);c=np.searchsorted(ids,post);mask=(a<len(ids))&(c<len(ids));a=np.minimum(a,len(ids)-1);c=np.minimum(c,len(ids)-1);mask&=(ids[a]==pre)&(ids[c]==post)&(w>0)
 pres.append(a[mask].astype(np.int32));posts.append(c[mask].astype(np.int32));weights.append(w[mask].astype(np.float32))
 if i%300==0:print(i,reader.num_record_batches,flush=True)
w=coo_matrix((np.concatenate(weights),(np.concatenate(posts),np.concatenate(pres))),shape=(len(ids),len(ids))).tocsr();w.sum_duplicates()
np.save(OUT/'body_ids.npy',ids);save_npz(OUT/'counts.npz',w)
synapses=int(w.sum(dtype=np.float64));total_in=np.asarray(w.sum(axis=1)).ravel();w.data/=np.repeat(np.maximum(total_in,1),np.diff(w.indptr));save_npz(OUT/'normalized.npz',w)
sha=hashlib.sha256()
with source.open('rb') as f:
 for chunk in iter(lambda:f.read(8*1024*1024),b''):sha.update(chunk)
meta={'dataset':'male-cns:v1.0','neurons':len(ids),'edges':w.nnz,'synapses':synapses,'source_segment_edges':total,'excluded_segment_edges':total-w.nnz,'source':'https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/connectome-weights-male-cns-v1.0-minconf-0.5.feather','source_sha256':sha.hexdigest(),'ids_sha256':hashlib.sha256(ids.tobytes()).hexdigest(),'csr_sha256':hashlib.sha256(w.indptr.tobytes()+w.indices.tobytes()+w.data.tobytes()).hexdigest(),'sparse_bytes':w.data.nbytes+w.indices.nbytes+w.indptr.nbytes,'build_wall_seconds':time.monotonic()-start,'scope':'All cached neuPrint Neuron records, including incomplete/untyped. Every positive edge between those records retained. Non-neuron segment fragments excluded. Incoming weights normalized; all-positive rate dynamics are an engineered model, not validated biophysical dynamics.'}
(OUT/'manifest.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta),flush=True)
