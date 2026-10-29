"""Verify and restore a complete past development epoch for readiness builds."""

from __future__ import annotations

import hashlib
import json
import subprocess

import joblib
import pandas as pd

from prahari.config import Config
from prahari.data.firewall import write_real_table
from prahari.data.uci import sha256_file


def verify_requirements(config: Config, path: str, original_hash: str) -> None:
    """Permit added dependencies, never changes to the trained environment pins."""
    current = (config.root / path).read_bytes()
    if hashlib.sha256(current).hexdigest() == original_hash:
        return
    versions = subprocess.check_output(["git", "log", "--format=%H", "--", path], cwd=config.root).decode().splitlines()
    for version in versions:
        raw = subprocess.check_output(["git", "show", version + ":" + path], cwd=config.root)
        for candidate in (raw, raw.replace(b"\r\n", b"\n"), raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")):
            if hashlib.sha256(candidate).hexdigest() != original_hash:
                continue
            pins = lambda value: {line.strip() for line in value.decode().splitlines()
                                  if line.strip() and not line.lstrip().startswith("#")}
            if not pins(candidate).issubset(pins(current)):
                raise ValueError("A trained benchmark dependency pin changed")
            return
    raise ValueError("Cannot verify the cached benchmark dependency epoch")


def restore_development_cache(config: Config) -> None:
    """Reuse verified unsealed development artifacts; never open final data.

    Indian collection/app edits do not require rerunning nested foreign CV.
    Learning code, learner settings, seed, input hashes and model hashes must
    still match. This option is restricted to the explicitly labelled demo.
    """
    settings = config.section("benchmark_config")
    cache = config.base["pipeline"]["readiness_benchmark_cache"]
    entries = json.loads(config.path("benchmark_model_manifest").read_text(encoding="utf-8"))
    expected = {(name, "full", variant) for name in settings["datasets"]
                for variant in [*settings["models"]["imbalance_variants"], "logistic"]}
    expected |= {(name, "harmonized", "none") for name in settings["hdm"]["datasets"]}
    observed = [(entry["dataset"], entry["representation"], entry["variant"]) for entry in entries]
    if len(observed) != len(expected) or set(observed) != expected:
        raise ValueError("Cached benchmark manifest is incomplete")
    rows, audit, fingerprints = [], {}, []
    for entry in entries:
        if entry["horizon_quarters"] != settings["datasets"][entry["dataset"]]["horizon_quarters"]:
            raise ValueError("Cached benchmark horizon metadata changed")
        artifact = (config.root / entry["artifact"]).resolve()
        if not artifact.is_relative_to(config.path("models").resolve()):
            raise ValueError("Benchmark artifact escapes its configured directory")
        receipt = json.loads(artifact.with_suffix(".development.json").read_text(encoding="utf-8"))
        if receipt["entry"] != entry or receipt["artifact_sha256"] != sha256_file(artifact):
            raise ValueError("Cached benchmark model integrity failure")
        training = config.path("benchmark_training_dir") / (entry["dataset"] + ".parquet")
        if receipt["identity"]["training_sha256"] != sha256_file(training):
            raise ValueError("Cached benchmark training input changed")
        fingerprint = receipt["identity"]["fingerprint"]
        for path in cache["learning_files"]:
            if fingerprint.get(path) != sha256_file(config.root / path):
                raise ValueError("Cached benchmark learning code/settings changed: " + path)
        model = joblib.load(artifact)
        if model.pipeline.named_steps["model"].get_params()["random_state"] != config.seed:
            raise ValueError("Cached benchmark seed changed")
        fingerprints.append(fingerprint)
        rows.extend(receipt["rows"])
        audit[artifact.stem] = receipt["folds"]
    if any(fingerprint != fingerprints[0] for fingerprint in fingerprints[1:]):
        raise ValueError("Cached benchmark models mix training epochs")
    verify_requirements(config, cache["requirements"], fingerprints[0][cache["requirements"]])
    write_real_table(pd.DataFrame(rows), config.path("benchmark_development_metrics"))
    config.path("benchmark_audit").write_text(json.dumps(audit, indent=2), encoding="utf-8")
