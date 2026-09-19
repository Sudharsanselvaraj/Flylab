"""Select a separate visual / central-complex substrate; never edit looming data."""
import hashlib,json
from pathlib import Path
import pandas as pd
from hawking_fly.connectome.client import ConnectomeClient
ROOT=Path(__file__).resolve().parents[1]
n=pd.read_parquet(ROOT/'data/anatomy/neurons.parquet')
pattern=r'^(MeTu2a|MeTu2b|TuBu\d+|ER.*|EPG|PEN_a\(PEN1\)|PEN_b\(PEN2\)|PFL[123])$'
n=n[n.type.fillna('').str.match(pattern)].sort_values('bodyId')
ids=[int(x) for x in n.bodyId]
c=ConnectomeClient().client
q=f'MATCH (a:Neuron)-[e:ConnectsTo]->(b:Neuron) WHERE a.bodyId IN {ids} AND b.bodyId IN {ids} RETURN a.bodyId AS pre, b.bodyId AS post, e.weight AS weight ORDER BY pre, post'
edges=c.fetch_custom(q)
records=[]
for row in n.itertuples():
    p=row.somaLocation if isinstance(row.somaLocation,dict) else row.tosomaLocation
    records.append(dict(body_id=str(row.bodyId),type=row.type,side=row.side,position=[float(v) for v in p['coordinates']] if isinstance(p,dict) and p.get('coordinates') is not None else None,input=row.type.startswith('MeTu')))
g=dict(dataset='male-cns:v1.0',selection_regex=pattern,nodes=records,edges=json.loads(edges.to_json(orient='records')),source='https://male-cns.janelia.org/download/',license='CC-BY — FlyEM/Janelia and collaborators',coordinate_units='8 nm native voxels',dynamics_validated=False,flyvis_to_malecns_mapping_verified=False,scope='Separate visual / central-complex anatomical reservoir. Not a validated coding circuit.',weight_model='All-positive normalized synapse counts; neurotransmitter signs not modeled.')
g['sha256']=hashlib.sha256(json.dumps(g,sort_keys=True).encode()).hexdigest()
p=ROOT/'experiments/coding_fly/graph.json';p.write_text(json.dumps(g,separators=(',',':')))
print(json.dumps({'neurons':len(n),'edges':len(edges),'synapses':int(edges.weight.sum()),'sha256':g['sha256']}))
