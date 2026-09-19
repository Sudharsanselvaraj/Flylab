"""Guard FlyLab's retained API while retiring the separate Hawking experiment."""
from fastapi.testclient import TestClient
from hawking_fly.api.app import app
import pytest
from starlette.websockets import WebSocketDisconnect


def test_flylab_routes_remain_and_legacy_experiment_is_removed():
    with TestClient(app) as client:
        assert client.get('/api/health').json()['application'] == 'FlyLab'
        assert client.get('/api/physical-coding/catalog').status_code == 200
        assert client.get('/api/physical-coding/sessions').status_code == 200
        assert client.get('/api/experiments').status_code == 404
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/api/live/stream'):
                pass
        paths = client.get('/openapi.json').json()['paths']
    assert '/api/coding/recording' in paths
    assert '/api/anatomy/neuron/{body_id}' in paths
    assert not any(p.startswith('/api/live') or p.startswith('/api/experiments') for p in paths)
