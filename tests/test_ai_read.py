"""AI deep-read: prompt, parse, hash, CLI locate, and config defaults."""
import tempfile
from pathlib import Path
from unittest.mock import patch

from apps.workbench.bidmonitor_workbench.collectors.ai_read import (
    DEFAULT_AI_SETTINGS, build_prompt, compute_hash, locate_deerflow_cli, parse_result,
)
from apps.workbench.bidmonitor_workbench.storage.workbench import WorkbenchStore


def make_store():
    tmp = tempfile.mkdtemp()
    return WorkbenchStore(str(Path(tmp) / "bids.db"))


PROJECT = dict(title='政务云服务器采购项目', budget='500 万元', deadline='2026-11-30',
               purchaser='某市大数据局', win_company='', win_amount='',
               content='本项目采购 GPU 服务器 20 台，用于政务大模型推理。要求支持国产化信创环境。')


def test_parse_result_strips_json_fence():
    text = '```json\n{"采购单位": "某市大数据局", "预算": "500 万元"}\n```'
    result = parse_result(text)
    assert result['采购单位'] == '某市大数据局'


def test_parse_result_handles_plain_json():
    result = parse_result('{"预算": "500 万元"}')
    assert result['预算'] == '500 万元'


def test_parse_result_invalid_degrades():
    result = parse_result('这不是 JSON')
    assert result['error']
    assert 'raw' in result


def test_build_prompt_contains_fields_and_truncates_body():
    conf = dict(detail_len=2000)
    prompt = build_prompt(PROJECT, conf)
    assert '政务云服务器采购项目' in prompt
    assert '500 万元' in prompt
    assert '某市大数据局' in prompt
    assert 'GPU 服务器' in prompt
    conf_short = dict(detail_len=10)
    prompt_short = build_prompt(dict(content='很长的正文内容' * 20), conf_short)
    assert len(prompt_short) < 100


def test_compute_hash_changes_with_content():
    conf = dict(detail_len=2000)
    h1 = compute_hash(PROJECT, conf)
    changed = dict(PROJECT, content='正文完全改变，不同内容')
    h2 = compute_hash(changed, conf)
    assert h1 != h2


def test_locate_deerflow_cli_uses_explicit_path():
    assert locate_deerflow_cli(dict(deerflow_cli='/custom/deerflowcli')) == '/custom/deerflowcli'


def test_locate_deerflow_cli_falls_back_to_which():
    with patch('shutil.which', return_value='/usr/bin/deerflowcli'):
        assert locate_deerflow_cli(dict(deerflow_cli='')) == '/usr/bin/deerflowcli'


def test_default_settings_shape():
    assert DEFAULT_AI_SETTINGS['enabled'] is False
    assert DEFAULT_AI_SETTINGS['gateway'] == 'http://127.0.0.1:8001'
    assert 0 < DEFAULT_AI_SETTINGS['auto_limit'] <= 100


def test_store_seeds_ai_settings():
    store = make_store()
    conf = store.setting('ai_read_settings')
    assert conf['enabled'] is False
    assert conf['gateway'] == 'http://127.0.0.1:8001'


def test_ai_read_upsert_and_fetch():
    store = make_store()
    key, _ = store.upsert_project(dict(title='某项目', url='https://e.com/1', source='测试', published_at='2026-11-20'))
    store.save_ai_read(key, status='ready', result={'预算': '500 万元'}, error='', input_hash='abc')
    row = store.ai_read(key)
    assert row['status'] == 'ready'
    assert row['result']['预算'] == '500 万元'
    assert row['input_hash'] == 'abc'


def test_ai_read_marks_error():
    store = make_store()
    key, _ = store.upsert_project(dict(title='某项目', url='https://e.com/2', source='测试', published_at='2026-11-20'))
    store.save_ai_read(key, status='error', result={}, error='未配置 deerflow CLI 路径', input_hash='')
    row = store.ai_read(key)
    assert row['status'] == 'error'
    assert row['error']
