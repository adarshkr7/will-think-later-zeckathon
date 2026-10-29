"""Bind feature caches to the public source snapshot that actually built them."""

from __future__ import annotations

import json
from pathlib import Path

from prahari.config import Config
from prahari.data.uci import sha256_file


def feature_input_fingerprint(config: Config) -> dict[str, str]:
    """Hash explicit public inputs only; never enumerate a sealed directory.

    A batch records its immutable source epoch. Later acquisition, corrections
    or feature-code changes require a fresh build before registration.
    """
    settings = config.base["feature_lineage"]
    paths = [config.file, *(config.path(key) for key in settings["config_paths"])]
    for name in config.section("manual_config")["tables"]:
        if not name.replace("_", "").isalnum() or "sealed" in name.casefold():
            raise ValueError("Feature lineage accepts public manual table names only")
        paths.append(config.path("manual") / f"{name}.csv")
    for pattern in settings["market_patterns"]:
        paths.extend(config.path("market_cache").glob(pattern))
    for root in settings["code_roots"]:
        paths.extend(config.root.joinpath(root).rglob("*.py"))
    paths.extend(config.root / name for name in settings["code_files"])
    result = {}
    for path in sorted(set(paths)):
        if not path.is_file():
            raise FileNotFoundError(f"Feature input missing: {path}")
        result[path.relative_to(config.root).as_posix()] = sha256_file(path)
    return result


def feature_receipt_path(config: Config, artifact: Path) -> Path:
    return artifact.with_name(artifact.name + config.base["feature_lineage"]["receipt_suffix"])


def write_feature_receipt(config: Config, artifact: Path, inputs: dict[str, str]) -> None:
    """Write after the production firewall has accepted the feature artifact."""
    payload = {"version": "public-feature-lineage-v1", "inputs": inputs,
               "artifact_sha256": sha256_file(artifact)}
    target = feature_receipt_path(config, artifact)
    temporary = target.with_suffix(target.suffix + ".partial")
    temporary.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    temporary.replace(target)


def verify_feature_receipt(config: Config, artifact: Path, inputs: dict[str, str]) -> None:
    """Reject old, mixed-epoch or modified caches before scientific registration."""
    path = feature_receipt_path(config, artifact)
    if not path.is_file():
        raise RuntimeError(f"Feature lineage receipt missing; rebuild: {artifact.name}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "public-feature-lineage-v1" or payload.get("inputs") != inputs:
        raise RuntimeError(f"Feature sources changed; rebuild: {artifact.name}")
    if payload.get("artifact_sha256") != sha256_file(artifact):
        raise RuntimeError(f"Feature artifact changed after its source receipt: {artifact.name}")
