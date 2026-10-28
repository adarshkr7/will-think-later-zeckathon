"""Read-only, containment-checked interface to an exported offline bundle."""

import json
from pathlib import Path

import pandas as pd

from prahari.data.firewall import assert_real


class OutputStore:
    def __init__(self, manifest: str | Path) -> None:
        path = Path(manifest).resolve()
        self.root = path.parent
        self.manifest = json.loads(path.read_text(encoding="utf-8"))

    def path(self, key: str, *parts: str) -> Path:
        path = (self.root / self.manifest["files"][key]).joinpath(*parts).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Output bundle path escapes its root")
        return path

    def frame(self, key: str) -> pd.DataFrame:
        return self.frame_at(key)

    def frame_at(self, key: str, *parts: str) -> pd.DataFrame:
        if key not in self.manifest["files"]:
            return pd.DataFrame()
        path = self.path(key, *parts)
        if not path.is_file():
            return pd.DataFrame()
        table = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
        assert_real(table)
        return table

    def text(self, key: str, *parts: str) -> str:
        if key not in self.manifest["files"]:
            return ""
        path = self.path(key, *parts)
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def filtered_frame(self, key: str, filters: list) -> pd.DataFrame:
        """Push selection into the exported parquet scan, without live scoring."""
        if key not in self.manifest["files"]:
            return pd.DataFrame()
        path = self.path(key)
        if not path.is_file():
            return pd.DataFrame()
        if path.suffix != ".parquet":
            raise ValueError("Filtered output scans require parquet")
        table = pd.read_parquet(path, filters=filters)
        assert_real(table)
        return table
