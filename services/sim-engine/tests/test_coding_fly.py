"""Causal boundaries and reproducibility of the independent coding experiment."""
import itertools,json
import numpy as np
import pytest
from pydantic import ValidationError
from hawking_fly.coding.core import ACTIONS,ART,Policy,Reservoir,graph,pixels_to_features,source_for,split,teacher
from hawking_fly.api.coding import Observation,Ack

def test_coding_graph_is_real_and_separate():
    g=graph();ids={n['body_id'] for n in g['nodes']}
    assert len(ids)==677 and len(g['edges'])==46149
    assert not any(n['type']=='DNp01' for n in g['nodes'])
    assert {'10001','10010'}.isdisjoint(ids)
    assert g['dynamics_validated'] is False and g['flyvis_to_malecns_mapping_verified'] is False
    assert all(str(e['pre']) in ids and str(e['post']) in ids and e['weight']>0 for e in g['edges'])
    assert sum(n['input'] for n in g['nodes'])==101

def test_observation_forbids_privileged_state():
    for extra in ('source','reward','target','task_id','error','DOM','truth'):
        with pytest.raises(ValidationError):Observation(tick=0,pixels=[0]*2304,**{extra:'secret'})
    for values in ([0]*2303,[float('nan')]*2304,[-1]*2304,[256]*2304):
        with pytest.raises(ValueError):pixels_to_features(values)

def test_neural_pixels_causally_change_state_and_silence_is_real():
    r=Reservoir();p=[80]*2304
    a,trace=r.encode(p,trace=True);b,again=r.encode(p,trace=True)
    np.testing.assert_array_equal(a,b);assert trace==again
    changed,_=r.encode([180]*2304);assert np.max(abs(a-changed))>.05
    ids=[n['body_id'] for n in r.nodes if n['input']]
    cut,cut_trace=r.encode(p,ids,trace=True);assert np.max(abs(a-cut))>.05
    assert all(cut_trace['rates'][i]==0 for i in r.inputs)
    assert all(e['neuron'] not in r.inputs for e in cut_trace['spikes'])
    assert all(1<=e['tick']<=16 for e in trace['spikes'])
    measured=np.bincount([e['neuron'] for e in trace['spikes']],minlength=len(r.nodes))
    expected=np.floor(np.sum([v['rates'] for v in trace['trajectory']],axis=0)*.02+1e-6).astype(int)
    np.testing.assert_array_equal(measured,expected)

def test_actual_connectivity_contributes_to_readout():
    r=Reservoir();a,_=r.encode([80]*2304);r.w.data[:]=0;b,_=r.encode([80]*2304)
    assert np.max(abs(a-b))>.05

def test_split_disjoint_and_oracle_is_offline():
    groups={s:{t for t in itertools.product(range(2,5),repeat=3) if split(t)==s} for s in ('train','validation','test')}
    assert tuple(map(len,groups.values()))==(17,5,5)
    assert groups['train'].isdisjoint(groups['test']) and groups['validation'].isdisjoint(groups['test'])
    assert teacher((2,3,4),(0,0,0))==0
    assert teacher((2,3,4),(1,0,0))==3
    assert teacher((2,3,4),(2,3,4))==12
    import inspect
    assert 'teacher(' not in inspect.getsource(Policy)
    assert len(ACTIONS)==13 and ACTIONS[-1]['token'] is None
    assert '<h1>' in source_for((2,3,4))

def test_checkpoint_deterministic_and_corruption_rejected(tmp_path):
    if not (ART/'trained_policy/policy.npz').exists():pytest.skip('Train checkpoint to verify inference')
    p=Policy();a=p.infer([100]*2304);b=p.infer([100]*2304)
    assert a==b
    with np.load(p.path) as archive:data={k:archive[k] for k in archive.files}
    data['graph_sha']='wrong';bad=tmp_path/'wrong.npz';np.savez(bad,**data)
    with pytest.raises(ValueError,match='mismatch'):Policy(bad)

def test_browser_evaluation_artifact():
    p=ART/'metrics/browser_evaluation.json'
    if not p.exists():pytest.skip('Run actual browser evaluation to verify evidence')
    data=json.loads(p.read_text())
    assert len(data['episodes'])==5
    assert data['replay']['exact']
    for e in data['episodes']:
        assert e['split']=='test' and e['events'] and e['decisions'] and e['observations']
        assert e['corrections']>=1
        assert isinstance(e['result']['success'],bool)
        assert all(m['tick']>m['decisionTick'] for m in e['events'])
    assert data['success_rate']==sum(e['result']['success'] for e in data['episodes'])/5
    assert data['success_rate']>=.8
    assert not data['perturbation']['result']['success']

def test_saved_visual_feedback_changes_the_learned_action():
    path=ART/'metrics/browser_evaluation.json'
    if not path.exists():pytest.skip('Browser evidence unavailable')
    episode=json.loads(path.read_text())['episodes'][0]
    p=Policy();actions=[]
    assert episode['checkpoint']==p.sha
    for pixels,decision in zip(episode['observations'][:2],episode['decisions'][:2]):
        action,neural,logits=p.infer(pixels,tick=decision['tick']-16)
        assert action==decision['action'] and neural==decision['neural'] and logits==decision['logits']
        actions.append(action)
    assert actions[0]!=actions[1] and actions[1]>=3
    # Holding the first image fixed repeats the first action rather than advancing a script.
    assert p.infer(episode['observations'][0])[0]==actions[0]

def test_websocket_rejects_out_of_order_or_privileged_inputs():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from hawking_fly.api.coding import router
    app=FastAPI();app.include_router(router)
    with TestClient(app).websocket_connect('/api/coding/stream') as ws:
        ws.send_json({'seed':37,'silenced':[]});assert ws.receive_json()['kind']=='ready'
        ws.send_json({'kind':'observe','tick':1,'pixels':[100]*2304})
        assert ws.receive_json()['kind']=='error'
    with TestClient(app).websocket_connect('/api/coding/stream') as ws:
        ws.send_json({'seed':37,'silenced':[]});ws.receive_json()
        ws.send_json({'kind':'observe','tick':0,'pixels':[100]*2304,'source':'hidden'})
        assert ws.receive_json()['kind']=='error'
