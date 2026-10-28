"""Rate-limited, checksummed public-source caching; blocks stop collection."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

import requests

from prahari.config import Config

LOG = logging.getLogger(__name__)


class SourceBlocked(RuntimeError):
    pass


class CachedDownloader:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.settings = config.section("india_config")["network"]
        self.session = requests.Session()
        self.session.headers.update(self.settings["headers"])
        self.last_request = 0.0

    def close(self) -> None:
        self.session.close()

    def register_manual(self, source: str, url: str, filename: str, local_path: Path) -> Path:
        """Register an actual human-downloaded file without overwriting cached bytes."""
        if Path(filename).name != filename or not source.replace("_", "").isalnum():
            raise ValueError("Invalid cache path")
        destination = self.config.path("raw") / source / filename
        payload = local_path.read_bytes()
        if destination.exists() and destination.read_bytes() != payload:
            raise ValueError("Refusing to overwrite an existing raw download")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            destination.write_bytes(payload)
        receipt = destination.with_suffix(destination.suffix + ".receipt.json")
        metadata = {"source_url": url, "sha256": hashlib.sha256(payload).hexdigest()}
        if receipt.exists() and json.loads(receipt.read_text(encoding="utf-8")) != metadata:
            raise ValueError("Manual import conflicts with cached provenance")
        receipt.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return destination

    def fetch(self, source: str, url: str, filename: str, *, offline: bool = False) -> Path:
        if Path(filename).name != filename or not source.replace("_", "").isalnum():
            raise ValueError("Cache names must not contain path traversal")
        path = self.config.path("raw") / source / filename
        receipt = path.with_suffix(path.suffix + ".receipt.json")
        if path.exists():
            metadata = json.loads(receipt.read_text(encoding="utf-8"))
            if metadata["source_url"] != url or metadata["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
                raise ValueError("Public-source cache integrity failure")
            return path
        if offline:
            raise FileNotFoundError(f"Offline public-source cache missing: {path}")
        failures = self.config.path("source_failures")
        if failures.exists():
            import pandas as pd
            recorded = pd.read_csv(failures)
            if (recorded.source.eq(source) & recorded.status.isin([401, 403, 429])).any():
                raise SourceBlocked(f"{source} remains blocked; use cached/manual files and resolve DATA_REQUESTS.md")
        blocks = 0
        for attempt in range(self.settings["max_attempts"]):
            pause = self.settings["interval_seconds"] - (time.monotonic() - self.last_request)
            if pause > 0:
                time.sleep(pause)
            try:
                self.last_request = time.monotonic()
                response = self.session.get(url, timeout=self.settings["timeout_seconds"])
                if response.status_code in (401, 403, 429):
                    blocks += 1
                    if blocks >= self.settings["block_attempts"]:
                        self._record_failure(source, url, path, response.status_code)
                        raise SourceBlocked(f"{source} repeatedly blocked; manual download recorded in DATA_REQUESTS.md")
                if response.status_code == 404:
                    raise FileNotFoundError(f"No official file for requested date: {url}")
                response.raise_for_status()
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(path.suffix + ".partial")
                temporary.write_bytes(response.content)
                temporary.replace(path)
                receipt.write_text(json.dumps({"source_url": url,
                    "sha256": hashlib.sha256(response.content).hexdigest()}, indent=2), encoding="utf-8")
                LOG.info("Cached source=%s bytes=%s", source, len(response.content))
                return path
            except requests.RequestException as exc:
                if attempt + 1 == self.settings["max_attempts"]:
                    self._record_failure(source, url, path, getattr(exc.response, "status_code", None))
                    raise
                time.sleep(self.settings["backoff_seconds"] * 2**attempt)
        raise RuntimeError("Download retry loop exhausted")

    def _record_failure(self, source: str, url: str, path: Path, status: int | None) -> None:
        # No response body, headers, cookies or session contents enter logs.
        LOG.error("Public download stopped: source=%s status=%s", source, status)
        import pandas as pd
        from prahari.data.firewall import write_real_table
        destination = self.config.path("source_failures")
        row = {"source": source, "source_url": url, "status": status,
               "target": str(path.relative_to(self.config.root)), "needs_verification": 1, "is_synthetic": 0}
        previous = pd.read_csv(destination) if destination.exists() else pd.DataFrame()
        result = pd.concat([previous, pd.DataFrame([row])], ignore_index=True).drop_duplicates(["source", "source_url"])
        write_real_table(result, destination)
        requests_path = self.config.path("data_requests")
        current = requests_path.read_text(encoding="utf-8")
        target = str(path.relative_to(self.config.root)).replace("\\", "/")
        if url not in current:
            with requests_path.open("a", encoding="utf-8") as stream:
                stream.write(f"\n- [ ] **P0 blocked public source ({status}).** Company: all securities in the requested archive; field: official market/source observations; period: {path.name}. Download [{source}]({url}) manually to `{target}`. For a manually supplied file, use the import command to create a checksummed receipt; do not fabricate missing observations.\n")
