"""Win/void announcements: schema columns, meta notice types, search visibility."""
import tempfile
from pathlib import Path

from apps.workbench.bidmonitor_workbench.storage.workbench import WorkbenchStore


def make_store():
    tmp = tempfile.mkdtemp()
    return WorkbenchStore(str(Path(tmp) / "bids.db"))


def test_schema_has_win_columns():
    store = make_store()
    with store.connection() as db:
        cols = {r[1] for r in db.execute("PRAGMA table_info(projects)")}
    assert "win_company" in cols
    assert "win_amount" in cols


def test_meta_offers_result_types():
    store = make_store()
    types = store.meta()["notice_types"]
    assert "中标结果" in types
    assert "废标终止" in types
    assert "合同公告" in types


from apps.workbench.bidmonitor_workbench.collectors.generic import parse_listing

SOURCE = dict(id='t', name='测试采购网', url='https://example.com/notices/', province='全国', adapter='generic')

WIN_HTML = '''<ul>
<li><a href="/notice/1.html">某设备采购项目中标结果公告</a><time>2026-11-20</time></li>
<li><a href="/notice/2.html">某设备采购项目废标公告</a><time>2026-11-20</time></li>
<li><a href="/notice/3.html">某设备采购项目招标公告</a><time>2026-11-20</time></li>
</ul>'''


def test_parse_listing_keeps_result_notices():
    rows = list(parse_listing(WIN_HTML, 'https://example.com/notices/', SOURCE))
    titles = {r['title'] for r in rows}
    assert any('中标结果' in t for t in titles)
    assert any('废标公告' in t for t in titles)
    assert any('招标公告' in t for t in titles)


def test_search_default_includes_results():
    store = make_store()
    store.upsert_project(dict(title='某设备采购项目中标结果公告', url='https://example.com/a', source='测试', published_at='2026-11-20'))
    store.upsert_project(dict(title='某设备采购项目招标公告', url='https://example.com/b', source='测试', published_at='2026-11-20'))
    result = store.search()
    assert result['total'] == 2
    filtered = store.search(notice_type='中标结果')
    assert filtered['total'] == 1
    assert filtered['items'][0]['title'].startswith('某设备采购项目中标结果')


from apps.workbench.bidmonitor_workbench.collectors.detail import extract_fields


def test_extract_fields_win_company_field_line():
    content = ('采购项目编号：A2026-001\n'
               '中标供应商：北京某某科技有限公司\n'
               '中标金额：286 万元\n')
    result = extract_fields(content)
    assert result['win_company'] == '北京某某科技有限公司'
    assert result['win_amount'] == '286 万元'


def test_extract_fields_win_company_table():
    content = ('项目名称：XX系统采购\n'
               '中标供应商名称：\n'
               '上海某某信息技术有限公司\n'
               '中标金额：\n'
               '1,200,000 元\n')
    result = extract_fields(content)
    assert '上海某某信息技术有限公司' in result['win_company']
    assert result['win_amount'] == '1200000 元'


def test_extract_fields_no_win_when_absent():
    content = '某项目招标公告，预算金额：50 万元。'
    result = extract_fields(content)
    assert not result.get('win_company')
    assert not result.get('win_amount')


import queue
import time
from unittest.mock import patch
from apps.workbench.bidmonitor_workbench.collectors.collection import DetailFetcher


def test_detail_fetcher_backfills_and_marks_error():
    store = make_store()
    key, _ = store.upsert_project(dict(title='某设备采购项目招标公告', url='https://example.com/b', source='测试', published_at='2026-11-20'))
    calls = []

    def fake_fetch(url):
        calls.append(url)
        if url.endswith('/bad'):
            raise ValueError('未获取到可用公告正文')
        return {'content': '招标正文', 'deadline': '2026-12-01', 'budget': '50 万元', 'win_company': '', 'win_amount': ''}

    fetcher = DetailFetcher(store, fetch=fake_fetch, rate_per_min=120)
    fetcher.run_once()
    with store.connection() as db:
        good = db.execute("SELECT detail_status,content,deadline FROM projects WHERE id=?", (key,)).fetchone()
    assert good['detail_status'] == 'ready'
    assert good['content'] == '招标正文'
    assert good['deadline'] == '2026-12-01'

    key2, _ = store.upsert_project(dict(title='某设备采购项目招标公告2', url='https://example.com/bad', source='测试', published_at='2026-11-20'))
    fetcher.run_once()
    with store.connection() as db:
        bad = db.execute("SELECT detail_status,detail_error FROM projects WHERE id=?", (key2,)).fetchone()
    assert bad['detail_status'] == 'error'
    assert '可用公告正文' in (bad['detail_error'] or '')


def test_detail_fetcher_prioritizes_manual_queue():
    store = make_store()
    key, _ = store.upsert_project(dict(title='某项目', url='https://example.com/1', source='测试', published_at='2026-11-20'))
    fetcher = DetailFetcher(store, fetch=lambda url: {'content': '正文'}, rate_per_min=120)
    fetcher.request(key, 'https://example.com/1')
    fetcher.run_once()
    with store.connection() as db:
        row = db.execute("SELECT detail_status,content FROM projects WHERE id=?", (key,)).fetchone()
    assert row['detail_status'] == 'ready'
    assert row['content'] == '正文'


def test_detail_fetcher_host_cooldown_skips():
    store = make_store()
    store.upsert_project(dict(title='某项目', url='https://blocked.example/1', source='测试', published_at='2026-11-20'))
    fetcher = DetailFetcher(store, fetch=lambda url: (_ for _ in ()).throw(ValueError('来源限制访问（HTTP 429）')), rate_per_min=120)
    fetcher.run_once()
    fetcher.run_once()
    assert 'blocked.example' in fetcher.host_cooldowns
