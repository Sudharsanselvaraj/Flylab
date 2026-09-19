"""Verify saved full-network evidence against native input and lossless events."""
import gzip,hashlib,json,struct,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def verify(folder):
 meta=json.loads((folder/'episode.json').read_text());archive=meta['spike_archive'];file=folder/'spikes.bin'
 assert file.stat().st_size==archive['events']*8
 digest=hashlib.sha256()
 with file.open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):digest.update(block)
 assert digest.hexdigest()==archive['sha256']
 pairs=np.memmap(file,dtype='<u4',mode='r',shape=(archive['events'],2));assert np.all(np.diff(pairs[:,0].astype(np.int64))>=0)
 with gzip.open(folder/'timeline.json.gz','rt') as f:timeline=json.load(f)
 native=0;rendered=0;packet_events=0;last_end=0
 for j,event in enumerate(timeline):
  if event.get('activity_file'):
   raw=(folder/event['activity_file']).read_bytes();magic,tick,n,count=struct.unpack('<4I',raw[:16]);assert magic==0x31534e43 and n==len(archive['neurons']) and tick==event['tick']
   batch=np.frombuffer(raw,dtype='<u4',offset=16+4*n).reshape(-1,2);assert len(batch)==count
   assert np.array_equal(pairs[last_end:last_end+count],batch);last_end+=count;packet_events+=count
  if event['kind']=='browser_input' and event['type']=='keydown':
   previous=timeline[j-1];assert previous['kind']=='motor' and previous['phase']=='contact' and previous['key']==event['key'] and previous['tick']==event['tick'];native+=1;rendered+=bool(previous.get('render_acknowledged'))
 for d in meta['decisions']:
  if d.get('readout_file'):assert hashlib.sha256((folder/d['readout_file']).read_bytes()).hexdigest()==d['readout_sha256']
 assert meta['initial']['source']==''
 if meta.get('result'):
  assert (folder/'index.html').read_text()==meta['result']['source']
  assert meta['result']['all_inputs_trusted']
 return {'session':folder.name,'mode':meta['mode'],'neurons':len(archive['neurons']),'archived_events':archive['events'],'streamed_events':packet_events,'native_keydowns':native,'renderer_acknowledged_keydowns':rendered,'result':meta.get('result'),'verified':True}
if __name__=='__main__':
 result=verify(ROOT/'experiments/physical_coding/sessions'/sys.argv[1]);out=ROOT/'experiments/full_cns'/f"verified-{sys.argv[1]}.json";out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
