"""Central configuration; paths are relative to the selected base configuration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        content = yaml.safe_load(stream)
    if not isinstance(content, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return content


class Config:
    def __init__(self, path: str | Path = "configs/base.yaml") -> None:
        self.file = Path(path).resolve()
        self.root = self.file.parent.parent
        self.base = read_yaml(self.file)

    @property
    def seed(self) -> int:
        return int(self.base["seed"])

    def path(self, key: str) -> Path:
        return self.root / self.base["paths"][key]

    def section(self, key: str) -> dict[str, Any]:
        return read_yaml(self.path(key))

    def setup_logging(self) -> None:
        logging.basicConfig(**self.base["logging"])
