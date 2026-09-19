"""Read-only cached public MaleCNS anatomy. No credentials enter the client."""
import json
from functools import lru_cache
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from hawking_fly.coding.core import ROOT

router=APIRouter(prefix='/api/anatomy')
CACHE=ROOT/'data/anatomy'
SOURCE='https://storage.googleapis.com/flyem-male-cns/v1.0/segmentation/skeletons-malecns/skeletons-swc/'

@lru_cache(maxsize=1)
def neurons():
    path=CACHE/'neurons.json'
    if not path.exists(): raise HTTPException(503,'Prepare the public anatomy cache with scripts/prepare_live_anatomy.py')
    return json.loads(path.read_text())

@router.get('/overview/{asset}')
def overview(asset:str):
    if asset not in ('overview.json','positions.bin','body_ids.bin','classes.bin','skeletons.json','circuit.json','circuit.bin'): raise HTTPException(404)
    file=CACHE/asset
    if not file.exists(): raise HTTPException(503,'Anatomy cache unavailable; run scripts/prepare_live_anatomy.py')
    return FileResponse(file,media_type='application/json' if asset.endswith('.json') else 'application/octet-stream',headers={'Cache-Control':'public, max-age=86400'})

@router.get('/skeleton/{body_id}')
def skeleton(body_id:int):
    if str(body_id) not in neurons(): raise HTTPException(404,'Neuron ID not in MaleCNS cache')
    directory=CACHE/'skeletons';directory.mkdir(exist_ok=True)
    file=directory/f'{body_id}.bin'
    if not file.exists():
        try:
            with urlopen(SOURCE+str(body_id)+'.swc',timeout=30) as response: raw=response.read()
            rows=np.loadtxt(raw.decode().splitlines());lookup={int(r[0]):r[2:5] for r in rows}
            segments=np.asarray([[*lookup[int(r[6])],*r[2:5]] for r in rows if int(r[6]) in lookup],dtype='<f4')
            (directory/f'{body_id}.swc').write_bytes(raw);segments.tofile(file)
        except (HTTPError,URLError,ValueError): raise HTTPException(404,'No available skeleton; no synthetic morphology is substituted')
    return FileResponse(file,media_type='application/octet-stream',headers={'Cache-Control':'public, max-age=86400'})

@router.get('/neuron/{body_id}')
def neuron(body_id:int):
    record=neurons().get(str(body_id))
    if record is None: raise HTTPException(404,'Unknown neuron')
    return record

@router.get('/partners/{body_id}')
def partners(body_id:int):
    if str(body_id) not in neurons(): raise HTTPException(404,'Unknown neuron')
    file=CACHE/f'partners-{body_id}.json'
    if file.exists(): return json.loads(file.read_text())
    from hawking_fly.connectome.client import ConnectomeClient
    client=ConnectomeClient().client
    # Typed integer ID only. LIMIT controls output; sums/counts below cover all edges.
    items={}
    for direction,pattern in [('upstream','(p:Neuron)-[e:ConnectsTo]->(n:Neuron)'),('downstream','(n:Neuron)-[e:ConnectsTo]->(p:Neuron)')]:
        prefix=f'MATCH {pattern} WHERE n.bodyId = {body_id} '
        totals=client.fetch_custom(prefix+'RETURN count(e) AS partners, sum(e.weight) AS synapses').iloc[0]
        rows=client.fetch_custom(prefix+'RETURN p.bodyId AS body_id, p.type AS type, e.weight AS synapses ORDER BY synapses DESC LIMIT 200')
        items[direction]={'total_partners':int(totals.partners),'total_synapses':int(totals.synapses or 0),'partners':json.loads(rows.to_json(orient='records')),'shown_limit':200}
    result={'dataset':'male-cns:v1.0','body_id':str(body_id),**items}
    file.write_text(json.dumps(result));return result
