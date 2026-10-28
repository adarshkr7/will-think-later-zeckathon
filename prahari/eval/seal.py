"""Once-only benchmark access. Do not run --final until development is frozen."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path

import joblib
import pandas as pd

from prahari.config import Config
from prahari.data.firewall import assert_real, write_real_table
from prahari.data.uci import download, load_dataset, sha256_file
from prahari.eval.metrics import benchmark_metrics
from prahari.features.harmonize import harmonize


def code_fingerprint(config: Config) -> dict[str, str]:
    paths = [config.file, *config.file.parent.glob("*.yaml"),
             *config.root.joinpath("prahari").rglob("*.py"),
             *config.root.joinpath("scripts").rglob("*.py"),
             config.root / "requirements.txt", config.root / "pyproject.toml"]
    return {str(path.relative_to(config.root)).replace("\\", "/"): sha256_file(path)
            for path in sorted(set(paths)) if path.is_file()}


def freeze_benchmark(config: Config) -> None:
    """Freeze model hashes and code for final evaluation, without reading seals."""
    lock = config.path("benchmark_lock")
    manifest = config.path("benchmark_model_manifest")
    records = json.loads(manifest.read_text(encoding="utf-8"))
    payload = {"files": code_fingerprint(config), "manifest_sha256": sha256_file(manifest),
               "models": {entry["artifact"]: sha256_file(config.root / entry["artifact"]) for entry in records},
               "training": {str(path.relative_to(config.root)).replace("\\", "/"): sha256_file(path)
                            for path in config.path("benchmark_training_dir").iterdir()
                            if path.suffix in (".json", ".parquet")}}
    if lock.exists():
        if json.loads(lock.read_text(encoding="utf-8")) != payload:
            raise ValueError("Benchmark already frozen with different code/models")
        return
    lock.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def verify_benchmark_lock(config: Config) -> list[dict]:
    lock = json.loads(config.path("benchmark_lock").read_text(encoding="utf-8"))
    manifest = config.path("benchmark_model_manifest")
    if lock["files"] != code_fingerprint(config) or lock["manifest_sha256"] != sha256_file(manifest):
        raise ValueError("Frozen benchmark files changed")
    for path, digest in lock["models"].items():
        if sha256_file(config.root / path) != digest:
            raise ValueError("Frozen model changed")
    for path, digest in lock["training"].items():
        if sha256_file(config.root / path) != digest:
            raise ValueError("Frozen training partition/metadata changed")
    return json.loads(manifest.read_text(encoding="utf-8"))


def claim_once(path: Path) -> None:
    """Atomic claim before access; a failed final run also consumes the claim."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump({"state": "claimed", "opened_at": pd.Timestamp.now(tz="UTC").isoformat()}, stream)
    except FileExistsError as exc:
        raise RuntimeError("Final evaluation was already claimed; refusing a second opening") from exc


def _open_reserved(config: Config, dataset: str) -> pd.DataFrame:
    directory = config.path("benchmark_seal_dir")
    payload = json.loads((directory / f"holdout_{dataset}.json").read_text(encoding="utf-8"))
    canonical = json.dumps(payload["indices"], separators=(",", ":"))
    if hashlib.sha256(canonical.encode()).hexdigest() != payload["sha256"]:
        raise ValueError("Sealed membership hash mismatch")
    table = pd.read_parquet(directory / f"holdout_{dataset}.parquet").set_index("row_id")
    if sorted(table.index.tolist()) != payload["indices"]:
        raise ValueError("Sealed partition membership mismatch")
    assert_real(table)
    # Inside the final boundary only: verify every reserved value against the
    # original checksummed source, not merely its row membership.
    metadata = json.loads((config.path("benchmark_training_dir") / f"{dataset}.json").read_text(encoding="utf-8"))
    spec = config.section("benchmark_config")["datasets"][dataset]
    source = download(config, spec["source"], offline=True)
    if sha256_file(source) != metadata["source_sha256"]:
        raise ValueError("Original benchmark source changed")
    original = load_dataset(config, dataset, offline=True)
    pd.testing.assert_frame_equal(table.sort_index(), original.loc[payload["indices"]].sort_index())
    return table


def evaluate_final(config: Config) -> None:
    entries = verify_benchmark_lock(config)
    claim_once(config.path("benchmark_ledger"))
    settings = config.section("benchmark_config")
    mapping = config.section("harmonized_map")
    policy = config.section("policy_config")
    partitions = {name: _open_reserved(config, name) for name in settings["datasets"]}
    rows = []
    for entry in entries:
        model = joblib.load(config.root / entry["artifact"])
        for dataset in [entry["dataset"], *(["taiwan"] if entry["representation"] == "harmonized" else [])]:
            table = partitions[dataset]
            if set(model.fit_indices).intersection(table.index) and dataset == entry["dataset"]:
                raise AssertionError("Model fit indices overlap reserved rows")
            if dataset != entry["dataset"] and set(model.transfer_preprocessor.fit_indices_).intersection(table.index):
                raise AssertionError("Transfer preprocessing saw reserved target-country rows")
            if entry["representation"] == "harmonized":
                X = harmonize(table, settings["datasets"][dataset]["source"], mapping, shared_only=True)
            else:
                X = table[model.columns]
            probabilities = model.predict_transfer(X) if dataset != entry["dataset"] else model.predict(X)
            row = benchmark_metrics(table.target.to_numpy(), probabilities, settings["metrics"], policy, config.seed)
            rows.append({**row, **{k: v for k, v in entry.items() if k != "artifact"},
                         "evaluation_dataset": dataset, "evaluation_split": "untouched_holdout",
                         "is_transfer": int(dataset != entry["dataset"])})
    write_real_table(pd.DataFrame(rows), config.path("benchmark_final_metrics"))


def evaluate_final_sealed(config: Config) -> None:
    """One final opening of a collector-prepared full-cohort feature artifact.

    The collector supplies the artifact's SHA-256 and case count in the
    registered config, without revealing cases. The artifact contains complete
    dated cross-sections (not a tiny sealed-only ranking universe), a binary
    is_sealed_case marker, and no outcome columns. All checks that can run
    without reading the envelope precede its atomic, irrevocable access claim.
    """
    from prahari.eval.preregistration import preflight, verify
    from prahari.data.artifacts import load_hdm_models
    from prahari.models.scoring import score_snapshot
    from prahari.policy.watchlist import build_watchlist
    registration = verify(config)
    preflight(config)
    if not config.path("benchmark_final_metrics").is_file() or not config.path("india_metrics").is_file():
        raise RuntimeError("Complete registered public evaluation before opening sealed cases")
    sealed = config.section("model_config")["sealed"]
    digest = sealed.get("input_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or not isinstance(sealed.get("expected_cases"), int) or sealed["expected_cases"] <= 0:
        raise RuntimeError("Independent collector must declare the sealed artifact hash and case count before registration")
    models = load_hdm_models(config)
    claim_once(config.path("indian_sealed_ledger"))
    # First protected access is below this line. A failed run stays consumed.
    source = config.path("indian_sealed_input")
    if sha256_file(source) != digest:
        raise ValueError("Sealed artifact differs from the collector's registered hash")
    table = pd.read_parquet(source)
    assert_real(table)
    if not {"is_sealed_case", "arena", "scoring_date", "max_source_date"}.issubset(table):
        raise ValueError("Sealed artifact must contain full dated feature cross-sections and a case marker")
    if not table.is_sealed_case.isin([0, 1]).all() or table.loc[table.is_sealed_case.eq(1), "entity_id"].nunique() != sealed["expected_cases"]:
        raise ValueError("Sealed case marker/count mismatch")
    table["scoring_date"] = pd.to_datetime(table.scoring_date, utc=True)
    table["max_source_date"] = pd.to_datetime(table.max_source_date, utc=True)
    if table.max_source_date.dropna().ge(table.loc[table.max_source_date.notna(), "scoring_date"]).any():
        raise ValueError("Sealed feature source crosses its scoring cutoff")
    rows = []
    settings, policy = config.section("model_config"), config.section("policy_config")
    for (arena, day), group in table.groupby(["arena", "scoring_date"]):
        if arena not in ("P", "U") or group.entity_id.duplicated().any():
            raise ValueError("Sealed cohort arena or identity ambiguity")
        selected_ids = set(group.loc[group.is_sealed_case.eq(1), "entity_id"])
        features = group.drop(columns="is_sealed_case").reset_index(drop=True)
        features.attrs["as_of"] = day.isoformat()
        scored, _ = score_snapshot(features, models, settings, arena)
        ranked = build_watchlist(scored, policy)
        ranked = ranked.loc[ranked.entity_id.isin(selected_ids)].copy()
        ranked["registration_hash"], ranked["evaluation_mode"] = registration, "once_only_sealed"
        rows.append(ranked)
    result = pd.concat(rows, ignore_index=True)
    write_real_table(result, config.path("indian_sealed_results"))
    config.path("indian_sealed_ledger").write_text(json.dumps({"state": "completed", "registration_hash": registration,
        "source_sha256": digest, "completed_at": pd.Timestamp.now(tz="UTC").isoformat()}), encoding="utf-8")
    logging.info("Final sealed scoring completed; no fitting or tuning was performed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze-benchmark", action="store_true")
    mode.add_argument("--final", action="store_true")
    mode.add_argument("--final-sealed", action="store_true")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    if args.freeze_benchmark:
        freeze_benchmark(config)
    elif args.final:
        evaluate_final(config)
    else:
        evaluate_final_sealed(config)


if __name__ == "__main__":
    main()
