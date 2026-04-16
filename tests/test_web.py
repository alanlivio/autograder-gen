import pytest
from web.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200

def test_api_validate_missing_data(client):
    response = client.post('/api/validate', json={})
    assert response.status_code == 400
    assert b'No config data provided' in response.data

def test_api_generate_missing_data(client):
    response = client.post('/api/generate', json={})
    assert response.status_code == 400
    assert b'No config data provided' in response.data
