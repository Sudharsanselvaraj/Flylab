import json
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from hawking_fly.api import anatomy
from hawking_fly.api.app import app


def test_anatomy_files_are_allowlisted_and_missing_data_is_explicit(tmp_path,monkeypatch):
    monkeypatch.setattr(anatomy,'CACHE',tmp_path)
    monkeypatch.setattr(anatomy,'neurons',lambda:{'10001':{'body_id':'10001','type':'DNp01','position':None}})
    with TestClient(app) as client:
        assert client.get('/api/anatomy/overview/secrets.json').status_code==404
        assert client.get('/api/anatomy/overview/positions.bin').status_code==503
        assert client.get('/api/anatomy/neuron/10001').json()['position'] is None
        assert client.get('/api/anatomy/skeleton/9999').status_code==404
        (tmp_path/'skeletons').mkdir()
        raw=np.array([0,0,0,1,2,3],dtype='<f4').tobytes()
        (tmp_path/'skeletons/10001.bin').write_bytes(raw)
        assert client.get('/api/anatomy/skeleton/10001').content==raw


def test_untyped_real_partners_serialize_as_null_not_nan(tmp_path,monkeypatch):
    from hawking_fly.connectome.client import ConnectomeClient
    class FakeNeuprint:
        def fetch_custom(self,query):
            if 'count(e)' in query:return pd.DataFrame([{'partners':1,'synapses':7}])
            return pd.DataFrame([{'body_id':42,'type':float('nan'),'synapses':7}])
    monkeypatch.setattr(anatomy,'CACHE',tmp_path)
    monkeypatch.setattr(anatomy,'neurons',lambda:{'10001':{}})
    monkeypatch.setattr(ConnectomeClient,'client',property(lambda _:FakeNeuprint()))
    with TestClient(app) as client:
        response=client.get('/api/anatomy/partners/10001')
        assert response.status_code==200
        assert response.json()['upstream']['partners'][0]['type'] is None
        assert response.json()['downstream']['total_synapses']==7
    json.loads((tmp_path/'partners-10001.json').read_text(),parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Invalid JSON number')))
