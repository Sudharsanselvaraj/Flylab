"""Acceptance boundaries exercised against real Chromium, not a mocked editor."""
import asyncio,gzip,inspect,json
import numpy as np
import pytest
from hawking_fly.physical_coding.browser import BrowserComputer,retinal_patches
from hawking_fly.physical_coding.motor import ComputerActuator,MotorAction,BY_CODE,DT
from hawking_fly.physical_coding.policy import ART,NeuralController,NeuralState

def test_empty_native_input_contact_gate_and_real_wrong_key():
    async def run():
        c=await BrowserComputer().open('Hello World');tick=0;events=[];before=[]
        async def advance(n):
            nonlocal tick
            tick+=n;await c.advance(round(n*DT*1000))
        async def publish(e):
            events.append({'tick':tick,**e})
            if e['kind']=='motor' and e['phase']=='contact':before.append((e['key'],(await c.audit())['source']))
        a=ComputerActuator(c,advance,publish)
        try:
            assert (await c.audit())['source']==''
            await a.focus();await a.character('h',override='KeyX')
            audit=await c.audit();assert audit['source']=='x'
            assert ('KeyX','') in before  # visible contact occurred before insertion
            assert all(e['trusted'] for e in audit['events'])
            native=next(e for e in audit['events'] if e['type']=='keydown')
            contact=next(e for e in events if e.get('phase')=='contact' and e.get('key')=='KeyX')
            assert native['time']==pytest.approx(contact['tick']*DT*1000)
            assert a.contact(contact['effector'])=='KeyX'
            png=await c.screenshot();assert retinal_patches(png)[1]  # real editor focus
            await a.stroke('Backspace');await a.character('H')
            assert (await c.audit())['source']=='H'
            # Missing physical contact MUST prevent browser input.
            a.contact=lambda _:None
            with pytest.raises(RuntimeError,match='withheld'):await a.stroke('KeyA')
            assert (await c.audit())['source']=='H'
        finally:await c.close()
    asyncio.run(run())

def test_contact_publish_failure_prevents_input():
    async def run():
        c=await BrowserComputer().open('Hello World')
        async def advance(n):await c.advance(n*2)
        async def publish(e):
            if e.get('phase')=='contact':raise RuntimeError('Renderer did not acknowledge contact')
        a=ComputerActuator(c,advance,publish)
        try:
            with pytest.raises(RuntimeError,match='acknowledge'):await a.stroke('KeyA')
            assert (await c.audit())['source']==''
            assert not any(e['type']=='keydown' for e in (await c.audit())['events'])
        finally:await c.close()
    asyncio.run(run())

def test_neural_state_continues_through_motor_time_and_silencing():
    n=NeuralState();n.stimulus(np.full(144,.5));a=n.advance(16);phase=n.phase.copy();b=n.advance(16)
    assert n.tick==32 and not np.array_equal(a,b) and not np.array_equal(phase,n.phase)
    cut=NeuralState([v['body_id'] for v in n.nodes if v['input']]);cut.stimulus(np.full(144,.5));c=cut.advance(32)
    assert np.max(abs(c-b))>.05 and np.all(cut.r[cut.inputs]==0)
    assert all(e['neuron'] not in cut.inputs for e in cut.recent)
    # No privileged source, task, reward or audit enters the learned controller.
    assert list(inspect.signature(NeuralController.observe).parameters)==['self','png','advance','publish']

def test_physical_key_geometry_is_unique_and_labeled():
    for code,key in BY_CODE.items():
        assert key['label']
        p=key['position'].copy();p[1]-=.018
        assert ComputerActuator.contact(p)==code
        p[1]+=.1;assert ComputerActuator.contact(p) is None

def test_measured_acceptance_and_fault_recovery_artifacts():
    data=json.loads((ART/'evaluation.json').read_text())
    expected=NeuralController().sha
    successful=[]
    for ep in data['episodes']:
        assert ep['checkpoint_sha256']==expected
        if ep['condition']=='silenced':assert not ep['success'];continue
        assert ep['success'] and ep['all_inputs_trusted'] and ep['pixel_mae']==0
        folder=ART/'sessions'/ep['session'];meta=json.loads((folder/'episode.json').read_text())
        assert meta['initial']['source']==''
        with gzip.open(folder/'timeline.json.gz','rt') as f:timeline=json.load(f)
        assert all(a['tick']<=b['tick'] for a,b in zip(timeline,timeline[1:]))
        for i,event in enumerate(timeline):
            if event['kind']=='browser_input' and event['type']=='keydown':
                previous=timeline[i-1]
                assert previous['kind']=='motor' and previous['phase']=='contact'
                assert previous['key']==event['key'] and previous['tick']==event['tick']
        assert (folder/'index.html').read_text()==ep['source']
        if ep['condition']=='wrong-key':
            assert ep['corrections']>=1
            bad=next(e for e in timeline if e['kind']=='audit' and 'Hellox' in e['source'])
            assert bad['score']['pixel_mae']>0
            correction=next(d for d in meta['decisions'] if d['mode']=='BACKSPACE')
            assert correction['visual_reading']['preview']=='Hellox'
            assert correction['tick']>bad['tick']
        successful.append([(d['mode'],d['character']) for d in meta['decisions']])
    assert data['restored_decisions_exact']
    assert successful[0]!=successful[2] # changed target changes the action stream

def test_checkpoint_training_changed_parameters_and_resume_state_exists():
    import torch
    for name in ('neural_glyph_readout','heading_transducer','generic_edit_gate'):
        p=torch.load(ART/(name+'-optimizer.pt'),weights_only=False)
        assert p['initial_parameter_sha256']!=p['final_parameter_sha256']
        assert p['optimizer']['state'] and p['epoch']>=500
        assert p['history'][-1]['loss']<p['history'][0]['loss']
    manifest=json.loads((ART/'manifest.json').read_text())
    groups=manifest['split'];assert set(groups['train']).isdisjoint(groups['test'])
    assert len(manifest['training_episodes'])==3

def test_websocket_forbids_source_or_client_motor_commands():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from hawking_fly.api.physical_coding import router
    app=FastAPI();app.include_router(router)
    with TestClient(app).websocket_connect('/api/physical-coding/stream') as ws:
        ws.send_json({'target':'Hello World','source':'injected'})
        assert ws.receive_json()['kind']=='error'

def test_continuous_motor_typing_speed_and_native_clock():
    async def run():
        c=await BrowserComputer().open('Typing');tick=0;contacts=[]
        async def advance(n):
            nonlocal tick
            tick+=n;await c.advance(n*2)
        async def publish(e):
            if e.get('phase')=='contact' and e.get('key','').startswith('Key'):
                contacts.append((tick,e['key'],e['effector']))
        a=ComputerActuator(c,advance,publish)
        try:
            await a.focus();start=tick
            for ch in 'asdfghjkl':await a.character(ch)
            audit=await c.audit();rate=9/((tick-start)*DT)
            assert 8<=rate<=15
            assert audit['source']=='asdfghjkl'
            downs=[e for e in audit['events'] if e['type']=='keydown']
            assert len(downs)==9 and all(e['trusted'] for e in downs)
            for contact,event in zip(contacts,downs):
                assert event['time']==pytest.approx(contact[0]*DT*1000)
                assert a.contact(contact[2])==event['code']
            assert a.position[2]==BY_CODE['KeyL']['position'][2] # no neutral reset
        finally:await c.close()
    asyncio.run(run())

def test_pixel_memory_only_reuses_unchanged_retinal_measurements():
    async def run():
        c=await BrowserComputer().open('Hello Fly');controller=NeuralController()
        async def advance(n):controller.neural.advance(n);await c.advance(n*2)
        async def publish(e):pass
        try:
            await advance(128) # the same measured resting warm-up as a live Session
            d1=await controller.observe(await c.screenshot(),advance,publish)
            assert d1['visual_reading']['target']=='Hello Fly'
            assert len(d1['retinal_refreshed_slots'])==80
            tick=controller.neural.tick
            d2=await controller.observe(await c.screenshot(),advance,publish)
            assert d2['retinal_refreshed_slots']==[] and controller.neural.tick==tick
            assert d2['readout_sample_ticks']==d1['readout_sample_ticks']
            a=ComputerActuator(c,advance,publish);await a.focus();await a.character('x')
            d3=await controller.observe(await c.screenshot(),advance,publish)
            assert d3['visual_reading']['editor']=='x' and d3['mode']=='BACKSPACE'
            assert 0<len(d3['retinal_refreshed_slots'])<80
        finally:await c.close()
    asyncio.run(run())
