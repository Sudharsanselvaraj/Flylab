"""Timing, provenance, and complete event recording at the live boundary."""
import asyncio,json,struct
import numpy as np
from hawking_fly.physical_coding.policy import NeuralState
from hawking_fly.physical_coding.telemetry import packet,SpikeArchive,MAGIC

def test_binary_transport_preserves_every_recorded_event(tmp_path):
    n=NeuralState();archive=SpikeArchive(tmp_path/'spikes.bin');n.spike_sink=archive.append;n.pending=[]
    n.stimulus(np.full(144,.5));n.advance(700);archive.close()
    rows=np.fromfile(tmp_path/'spikes.bin','<u4').reshape(-1,2)
    assert len(rows)>2048 and len(rows)==n.total_spikes==len(n.pending)
    assert np.all(np.diff(rows[:,0].astype(int))>=0)
    payload=packet(n.tick,n.frame()['rates'],n.pending)
    magic,tick,count,events=struct.unpack('<4I',payload[:16])
    assert (magic,tick,count,events)==(MAGIC,700,677,len(rows))
    assert np.array_equal(np.frombuffer(payload[16+count*4:],'<u4').reshape(-1,2),rows)
    assert np.allclose(np.frombuffer(payload,offset=16,count=count,dtype='<f4'),n.frame()['rates'])

def test_full_graph_preserves_neurons_and_propagates_beyond_subgraph():
    from hawking_fly.physical_coding.full_network import FullNeuralState,topology
    meta,ids,w=topology();n=FullNeuralState();n.stimulus(np.full(144,.5));before=n.r.copy();n.advance(2)
    assert len(ids)==meta['neurons']==176422 and w.nnz==meta['edges']==25862574
    assert len(n.read_indices)==576 and len(n.inputs)==101
    assert np.count_nonzero(n.r!=before)>100000 and np.isfinite(n.r).all()
    assert n.g['sha256']==meta['csr_sha256']
    blocked=FullNeuralState([str(ids[n.inputs[0]])]);blocked.stimulus(np.ones(144));blocked.advance(2)
    assert blocked.r[blocked.inputs[0]]==0

def test_pause_freezes_clock_and_preserves_render_gate():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from hawking_fly.api.physical_coding import router
    app=FastAPI();app.include_router(router)
    with TestClient(app).websocket_connect('/api/physical-coding/stream') as ws:
        ws.send_json({'target':'Hello Fly'})
        while True:
            event=ws.receive_json()
            if event['kind']=='ready':break
        ws.send_json({'kind':'start'});ws.send_json({'kind':'pause'})
        while True:
            raw=ws.receive()
            if raw.get('bytes'):continue
            e=json.loads(raw['text'])
            if e['kind']=='motor':ws.send_json({'kind':'rendered','tick':e['tick']})
            if e['kind']=='paused':frozen=e['tick'];break
        ws.send_json({'kind':'resume'})
        e=ws.receive_json();assert e=={'kind':'resumed','tick':frozen}
        # Disconnect during sensing is a stopped session, not a forged key.

def test_native_parallel_engine_preserves_complete_state_trajectory():
    import pytest
    from hawking_fly.physical_coding.full_network import FullNeuralState
    parallel=FullNeuralState()
    if parallel.engine!='Parallel GCD CSR CPU':pytest.skip('Optional verified macOS native kernel not built')
    reference=FullNeuralState();reference.matvec=lambda x:reference.w@x
    for patch in (np.linspace(-1,1,144),np.zeros(144),np.ones(144)):
        parallel.stimulus(patch);reference.stimulus(patch);parallel.advance(16);reference.advance(16)
        assert np.array_equal(parallel.r,reference.r)
        assert np.array_equal(parallel.phase,reference.phase)
        assert parallel.total_spikes==reference.total_spikes
        assert parallel.recent==reference.recent

def test_neuron_inspector_reads_complete_archive_and_rate_packets(tmp_path,monkeypatch):
    import gzip
    import hawking_fly.api.physical_coding as api
    sid='a'*32;folder=tmp_path/'sessions'/sid;folder.mkdir(parents=True)
    np.array([[1,0],[2,1],[3,1],[4,1]],dtype='<u4').tofile(folder/'spikes.bin')
    (folder/'activity-00001.bin').write_bytes(packet(4,[0,17.5],[{'tick':4,'neuron':1}]))
    (folder/'episode.json').write_text(json.dumps({'spike_archive':{'neurons':['10001','50002']}}))
    with gzip.open(folder/'timeline.json.gz','wt') as f:json.dump([{'kind':'neural','tick':4,'activity_file':'activity-00001.bin'},{'kind':'decision','tick':5,'id':'d0','mode':'TYPE','character':'a'}],f)
    monkeypatch.setattr(api,'ART',tmp_path)
    result=api.neuron_trace(sid,'50002')
    assert result['ticks']==[2,3,4] and result['count']==3
    assert result['rates']==[{'tick':4,'hz':17.5}]
    assert result['decisions'][0]['events_in_preceding_100ms']==3
    assert api.neuron_trace(sid,'99999')['simulated'] is False
