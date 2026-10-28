"""Cache original historical exchange filing indexes in bounded date windows.

Discovery only: index rows establish identity/dissemination evidence, not
financial values. Empty responses never establish complete financial coverage.
"""

from __future__ import annotations

import json
import logging
from urllib.parse import urlencode

import pandas as pd

from prahari.config import Config
from prahari.data.downloads import CachedDownloader
from prahari.data.firewall import write_real_table
from prahari.data.uci import sha256_file

LOG = logging.getLogger(__name__)


def collect_financial_indexes(config: Config, *, start: str | None, end: str | None, offline: bool) -> None:
    settings = config.section("financial_index_config")
    market = config.section("india_config")["market"]
    cursor, last = pd.Timestamp(start or market["start_date"]), pd.Timestamp(end or market["end_date"])
    if cursor > last:
        raise ValueError("Financial index start must precede its end")
    downloader = CachedDownloader(config)
    audit = []
    try:
        while cursor <= last:
            through = min(cursor+pd.Timedelta(days=settings["window_days"]-1), last)
            query = {"index": settings["index"], "period": settings["period"],
                     "from_date": cursor.strftime("%d-%m-%Y"), "to_date": through.strftime("%d-%m-%Y")}
            url = settings["url"]+"?"+urlencode(query)
            filename = settings["filename"].format(start=cursor.strftime("%Y%m%d"), end=through.strftime("%Y%m%d"))
            raw = downloader.fetch(settings["source"], url, filename, offline=offline)
            body = json.loads(raw.read_bytes())
            rows = body.get("data") if isinstance(body, dict) else body
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ValueError("Unrecognized original financial-results index")
            audit.append({"window_start": cursor.date(), "window_end": through.date(), "rows": len(rows),
                          "source_url": url, "source_doc": str(raw.relative_to(config.root)).replace("\\", "/"),
                          "sha256": sha256_file(raw), "status": "cached_index" if rows else "empty_unresolved",
                          "needs_verification": int(not rows), "is_synthetic": 0})
            LOG.info("Financial filing index %s through %s rows=%s dates_imputed=0; no statement values inferred", cursor.date(), through.date(), len(rows))
            cursor = through+pd.Timedelta(days=1)
    finally:
        downloader.close()
        if audit:
            target = config.path("financial_index_coverage")
            table = pd.DataFrame(audit)
            if target.exists():
                table = pd.concat([pd.read_csv(target), table], ignore_index=True)
                for key in ("window_start", "window_end"):
                    table[key] = table[key].astype(str)
                table = table.drop_duplicates(["window_start", "window_end"], keep="last")
            write_real_table(table, target)
