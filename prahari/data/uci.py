"""Cached, checksummed UCI downloads. No Indian records or synthetic rows."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests
from scipy.io import arff

from prahari.config import Config

LOG = logging.getLogger(__name__)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(config: Config, source: str, *, offline: bool = False) -> Path:
    spec = config.section("benchmark_config")["sources"][source]
    settings = config.base["downloads"]
    path = config.path("raw") / source / spec["archive"]
    receipt = path.with_suffix(".receipt.json")
    if path.exists():
        if not receipt.exists():
            raise ValueError(f"Missing download receipt: {receipt}")
        metadata = json.loads(receipt.read_text(encoding="utf-8"))
        if metadata["sha256"] != sha256_file(path) or metadata["source_url"] != spec["url"]:
            raise ValueError(f"Cache integrity failure: {path}")
        return path
    if offline:
        raise FileNotFoundError(f"Offline cache missing: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with requests.Session() as session:
        session.headers["User-Agent"] = settings["user_agent"]
        for attempt in range(settings["max_attempts"]):
            try:
                response = session.get(spec["url"], timeout=settings["timeout_seconds"])
                response.raise_for_status()
                payload = response.content
                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    if archive.testzip() is not None:
                        raise ValueError("Corrupt UCI zip")
                temporary = path.with_suffix(".partial")
                temporary.write_bytes(payload)
                temporary.replace(path)
                receipt.write_text(json.dumps({"source_url": spec["url"],
                                               "sha256": sha256_file(path)}, indent=2), encoding="utf-8")
                LOG.info("Cached %s (%s bytes)", source, len(payload))
                return path
            except requests.RequestException:
                if attempt + 1 == settings["max_attempts"]:
                    raise
                LOG.warning("UCI download failed for %s; attempt %s", source, attempt + 1)
                time.sleep(settings["backoff_seconds"] * 2**attempt)
    raise RuntimeError("Download retry loop exhausted")


def load_dataset(config: Config, name: str, *, offline: bool = False) -> pd.DataFrame:
    spec = config.section("benchmark_config")["datasets"][name]
    path = download(config, spec["source"], offline=offline)
    with zipfile.ZipFile(path) as archive:
        members = [member for member in archive.namelist() if Path(member).name == spec["member"]]
        if len(members) != 1:
            raise ValueError(f"Expected one {spec['member']} in archive")
        raw = archive.read(members[0])
    if spec["source"] == "polish":
        values, _ = arff.loadarff(io.StringIO(raw.decode("utf-8")))
        table = pd.DataFrame(values)
        table["target"] = table.pop("class").map({b"0": 0, b"1": 1})
    else:
        table = pd.read_csv(io.BytesIO(raw))
        table.columns = table.columns.str.strip()
        table = table.rename(columns={"Bankrupt?": "target"})
    if table["target"].isna().any() or not table["target"].isin([0, 1]).all():
        raise ValueError(f"Invalid target: {name}")
    if (len(table), int(table["target"].sum())) != (spec["rows"], spec["positives"]):
        raise ValueError(f"UCI count mismatch for {name}: {len(table)}, {table['target'].sum()}")
    table["is_synthetic"] = 0
    table["horizon_file"] = spec["member"]
    table["source_url"] = config.section("benchmark_config")["sources"][spec["source"]]["url"]
    table.index.name = "row_id"
    LOG.info("%s rows=%s positives=%s dates_imputed=0 missing=%s", name, len(table),
             int(table.target.sum()), table.isna().sum().loc[lambda s: s.gt(0)].to_dict())
    return table
