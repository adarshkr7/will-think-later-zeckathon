"""Freeze scientific inputs before replay; no sealed data are inspected here."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from prahari.config import Config
from prahari.data.quality import validate_manual
from prahari.data.manual import read_manual
from prahari.data.uci import sha256_file
from prahari.data.feature_lineage import (feature_input_fingerprint, feature_receipt_path,
                                         verify_feature_receipt)
from prahari.eval.panel_quality import audit_financial_histories, audit_market, panel_acceptance
from prahari.data.financials import financials_as_of
from prahari.data.quality import accounting_from_fields
from prahari.eval.seal import code_fingerprint


def registration_files(config: Config) -> dict[str, str]:
    files = code_fingerprint(config)
    files.update(feature_input_fingerprint(config))
    paths = [config.path("manual") / f"{name}.csv" for name in config.section("manual_config")["tables"]]
    paths += list(config.root.joinpath("app").rglob("*.py"))
    paths += [config.path("benchmark_model_manifest")]
    if config.path("benchmark_model_manifest").exists():
        entries = json.loads(config.path("benchmark_model_manifest").read_text(encoding="utf-8"))
        paths += [config.root / entry["artifact"] for entry in entries if entry["representation"] == "harmonized"]
    artifacts = [path for arena in config.base["pipeline"]["arenas"]
                 for path in config.path("feature_cache").joinpath(arena).glob("*.parquet")]
    paths += artifacts + [feature_receipt_path(config, path) for path in artifacts]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Registration input missing: {path.relative_to(config.root)}")
        files[str(path.relative_to(config.root)).replace("\\", "/")] = sha256_file(path)
    return dict(sorted(files.items()))


def preflight(config: Config) -> None:
    validate_manual(config)
    tolerance = config.section("manual_config")["validation"]["accounting_tolerance"]
    accounting = accounting_from_fields(financials_as_of(config, pd.Timestamp.now(tz="UTC")), tolerance)
    checks = panel_acceptance(read_manual(config, "events"), read_manual(config, "peers"), audit_market(config), accounting,
                              config.section("india_config")["panel"], audit_financial_histories(config))
    if not checks.passed.eq(1).all():
        failed = ", ".join(checks.loc[checks.passed.eq(0), "check"])
        raise RuntimeError("Registration refused; panel acceptance incomplete: " + failed)
    primary = config.section("model_config")["primary"]
    if not primary.get("prior_source") or any(value is None or not 0 < value < 1 for value in primary["priors"].values()):
        raise RuntimeError("Registration needs independently sourced Indian priors; panel prevalence is forbidden")
    chs = config.section("feature_config")["chs"]
    if any(chs.get(name) is None or not np.isfinite(chs[name]) or chs[name] <= 0 for name in ("price_cap_usd", "book_equity_floor_inr")):
        raise RuntimeError("CHS currency cap and book-equity floor must be declared before registration")
    if primary.get("nbfc_logit_scale") is None:
        raise RuntimeError("NBFC probability link must be declared before registration")
    dates = config.section("feature_config")["dates"]
    inputs = feature_input_fingerprint(config)
    for day in pd.date_range(dates["first_quarter"], dates["last_quarter"], freq="QE-MAR"):
        artifact = config.path("feature_cache") / "P" / f"{day:%Y-%m-%d}.parquet"
        if not artifact.is_file():
            raise RuntimeError("Panel feature history is incomplete")
        verify_feature_receipt(config, artifact, inputs)
    for arena in config.base["pipeline"]["arenas"]:
        if arena != "P":
            for artifact in config.path("feature_cache").joinpath(arena).glob("*.parquet"):
                verify_feature_receipt(config, artifact, inputs)


def freeze(config: Config, *, amend: str | None = None) -> None:
    preflight(config)
    path = config.path("preregistration_lock")
    payload = {"version": "zero-indian-label-v1", "files": registration_files(config)}
    if path.exists():
        original = json.loads(path.read_text(encoding="utf-8"))
        if original == payload:
            return
        if not amend or not amend.strip():
            raise RuntimeError("Registered inputs changed; explicit --amend reason required")
        log = {"time": pd.Timestamp.now(tz="UTC").isoformat(), "reason": amend,
               "previous_lock_sha256": sha256_file(path), "changed_files": sorted(set(payload["files"]) ^ set(original["files"]) |
                   {name for name in payload["files"].keys() & original["files"].keys() if payload["files"][name] != original["files"][name]})}
        config.path("amendments").parent.mkdir(parents=True, exist_ok=True)
        with config.path("amendments").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(log, sort_keys=True) + "\n")
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def verify(config: Config, *, require_committed: bool = True) -> str:
    path = config.path("preregistration_lock")
    if not path.exists():
        raise RuntimeError("No Indian pre-registration lock; replay is prohibited")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["files"] != registration_files(config):
        raise RuntimeError("Registered inputs changed; freeze with an explicit --amend reason before replay")
    if require_committed:
        relative = str(path.relative_to(config.root)).replace("\\", "/")
        status = subprocess.check_output(["git", "status", "--porcelain", "--", relative], cwd=config.root, text=True).strip()
        commit = subprocess.check_output(["git", "log", "-1", "--format=%H", "--", relative], cwd=config.root, text=True).strip()
        if status or not commit:
            raise RuntimeError("Pre-registration lock must be committed in its own commit before replay")
        changed = subprocess.check_output(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit], cwd=config.root, text=True).splitlines()
        if changed != [relative]:
            raise RuntimeError("The lock's latest commit must contain only that lock file")
    return sha256_file(path)
