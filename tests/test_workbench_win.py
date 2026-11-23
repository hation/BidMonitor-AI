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
