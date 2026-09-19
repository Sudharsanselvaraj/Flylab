"""Reproducible public MaleCNS anatomy cache. Run with repository PYTHONPATH.

Coordinates remain native 8 nm voxels. No synthetic positions or skeletons.
"""
import ast
import hashlib
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen
import numpy as np
import pandas as pd
from hawking_fly.coding.core import graph, ROOT
from hawking_fly.connectome.client import ConnectomeClient
OUT=ROOT/'data/anatomy';OUT.mkdir(parents=True,exist_ok=True)
SOURCE='https://storage.googleapis.com/flyem-male-cns/v1.0/segmentation/skeletons-malecns/skeletons-swc/'

def location(value):
    if isinstance(value,str): value=ast.literal_eval(value)
    if isinstance(value,dict): value=value.get('coordinates')
    if isinstance(value,(list,tuple,np.ndarray)) and len(value)==3 and np.isfinite(value).all(): return [float(v) for v in value]
    return None

def main():
    path=OUT/'neurons.parquet'
    if not path.exists():
        c=ConnectomeClient().client
        c.fetch_custom('MATCH (n:Neuron) RETURN n.bodyId AS bodyId, n.type AS type, n.somaLocation AS somaLocation, n.tosomaLocation AS tosomaLocation, n.somaSide AS side, n.superclass AS superclass').to_parquet(path)
    neurons=pd.read_parquet(path);records=[];positions=[];ids=[];classes=[];soma=0;root=0
    groups=sorted(neurons.superclass.dropna().unique().tolist())
    for n in neurons.itertuples():
        p=location(n.somaLocation);kind='soma'
        if p: soma+=1
        else:
            p=location(n.tosomaLocation);kind='to-soma location'
            if p: root+=1
        records.append({'body_id':str(n.bodyId),'type':n.type if pd.notna(n.type) else 'untyped','side':n.side if pd.notna(n.side) else None,
                        'position':p,'position_kind':kind if p else None,'superclass':n.superclass if pd.notna(n.superclass) else None})
        if p: positions.append(p);ids.append(n.bodyId);classes.append(groups.index(n.superclass)+1 if n.superclass in groups else 0)
    xyz=np.asarray(positions,dtype='<f4');xyz.tofile(OUT/'positions.bin');np.asarray(ids,dtype='<u4').tofile(OUT/'body_ids.bin');np.asarray(classes,dtype='u1').tofile(OUT/'classes.bin')
    (OUT/'neurons.json').write_text(json.dumps({n['body_id']:n for n in records},separators=(',',':')))
    meta={'dataset':'male-cns:v1.0','queried_neurons':len(neurons),'located_neurons':len(ids),'soma_count':soma,'tosoma_count':root,'missing_locations':len(neurons)-len(ids),
          'coordinate_units':'8 nm voxels','bounds':[xyz.min(axis=0).tolist(),xyz.max(axis=0).tolist()],'classes':['unclassified',*groups],
          'source':'https://male-cns.janelia.org/download/','license':'CC-BY','retrieved':'2026-09-19',
          'scope':'All neuPrint Neuron records; includes incomplete/untyped records. This is anatomy, not whole-CNS simulation.',
          'sha256':hashlib.sha256((OUT/'positions.bin').read_bytes()+(OUT/'body_ids.bin').read_bytes()).hexdigest()}
    (OUT/'overview.json').write_text(json.dumps(meta,indent=2))
    skeletons=OUT/'skeletons';skeletons.mkdir(exist_ok=True)
    def fetch(body):
        file=skeletons/f'{body}.bin';swc=skeletons/f'{body}.swc'
        if not swc.exists():
            with urlopen(SOURCE+body+'.swc',timeout=45) as response: swc.write_bytes(response.read())
        rows=np.loadtxt(swc);lookup={int(r[0]):r[2:5] for r in rows}
        segments=np.array([[*lookup[int(r[6])],*r[2:5]] for r in rows if int(r[6]) in lookup],dtype='<f4');segments.tofile(file)
        return {'body_id':body,'segments':len(segments),'sha256':hashlib.sha256(swc.read_bytes()).hexdigest()}
    result=[];failed=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(fetch,n['body_id']):n['body_id'] for n in graph()['nodes']}
        for future in as_completed(futures):
            try: result.append(future.result())
            except Exception as exc: failed.append({'body_id':futures[future],'error':type(exc).__name__})
    (OUT/'skeletons.json').write_text(json.dumps({'source':SOURCE,'units':'8 nm voxels','skeletons':sorted(result,key=lambda x:int(x['body_id'])),'unavailable':failed},indent=2))
    offsets=[];offset=0
    with (OUT/'circuit.bin').open('wb') as combined:
        for n in graph()['nodes']:
            file=skeletons/f"{n['body_id']}.bin"
            if not file.exists(): continue
            raw=file.read_bytes();combined.write(raw)
            offsets.append({'body_id':n['body_id'],'offset':offset,'floats':len(raw)//4});offset+=len(raw)//4
    (OUT/'circuit.json').write_text(json.dumps({'neurons':offsets,'source':SOURCE,'units':'8 nm voxels','unavailable':failed}))
    print(json.dumps({'overview':meta,'skeletons':len(result),'unavailable':failed}),flush=True)
if __name__=='__main__': main()
