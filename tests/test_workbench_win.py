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
