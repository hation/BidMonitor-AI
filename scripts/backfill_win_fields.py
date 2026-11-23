"""Backfill win_company/win_amount for existing result notices (idempotent)."""
import sys

from apps.workbench.bidmonitor_workbench.collectors.detail import extract_fields
from apps.workbench.bidmonitor_workbench.paths import database_path
from apps.workbench.bidmonitor_workbench.storage.workbench import WorkbenchStore


def backfill(store, limit=None):
    updated = 0
    while True:
        with store.connection() as db:
            rows = db.execute(
                "SELECT id,content FROM projects WHERE notice_type='中标结果' AND win_company='' AND content<>'' LIMIT 500"
            ).fetchall()
        if not rows:
            break
        for row in rows:
            fields = extract_fields(row['content'])
            win = {k: v for k, v in fields.items() if k in ('win_company', 'win_amount') and v}
            if win:
                store.set_detail(row['id'], win)
                updated += 1
        if limit and updated >= limit:
            break
    return updated


if __name__ == '__main__':
    store = WorkbenchStore(sys.argv[1] if len(sys.argv) > 1 else database_path())
    print(f"回填 {backfill(store)} 条中标公告的 win 字段")
