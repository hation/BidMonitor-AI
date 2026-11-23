"""Keyword editing: save, immediate effect, and input normalization."""
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from apps.workbench.bidmonitor_workbench.api import create_app


def make_client():
    tmp = tempfile.mkdtemp()
    return TestClient(create_app(str(Path(tmp) / 'test.db')))


def test_patch_saves_keywords():
    with make_client() as client:
        response = client.patch('/api/settings/opportunity-keywords', json={
            'core': ['服务器', '算力'], 'secondary': ['信息化'], 'exclude': ['复印纸'],
        })
        assert response.status_code == 200, response.text
        assert response.json()['saved'] is True
        assert response.json()['keywords']['core'] == ['服务器', '算力']


def test_save_takes_effect_immediately():
    with make_client() as client:
        client.post('/api/projects', json=dict(title='区块链存证平台采购项目', url='https://e.com/1',
                                               source='测试', published_at='2026-11-20'))
        assert client.get('/api/projects?relevance=direct').json()['total'] == 0
        client.patch('/api/settings/opportunity-keywords', json={
            'core': ['区块链', '存证'], 'secondary': [], 'exclude': [],
        })
        assert client.get('/api/projects?relevance=direct').json()['total'] == 1


def test_patch_rejects_non_array():
    with make_client() as client:
        response = client.patch('/api/settings/opportunity-keywords', json={
            'core': '服务器', 'secondary': [], 'exclude': [],
        })
        assert response.status_code == 400, response.text


def test_patch_normalizes_duplicates_and_blanks():
    with make_client() as client:
        response = client.patch('/api/settings/opportunity-keywords', json={
            'core': ['', '服务器', '服务器'], 'secondary': [], 'exclude': [],
        })
        assert response.status_code == 200
        assert response.json()['keywords']['core'] == ['服务器']


def test_patch_drops_overlong_words():
    with make_client() as client:
        response = client.patch('/api/settings/opportunity-keywords', json={
            'core': ['很长的词' * 11], 'secondary': [], 'exclude': [],
        })
        assert response.status_code == 200
        assert response.json()['keywords']['core'] == []


def test_meta_reflects_saved_keywords():
    with make_client() as client:
        client.patch('/api/settings/opportunity-keywords', json={
            'core': ['GPU'], 'secondary': [], 'exclude': [],
        })
        meta = client.get('/api/meta').json()
        assert meta['opportunity_keywords']['core'] == ['GPU']
