"""Once-only benchmark access. Do not run --final until development is frozen."""

from __future__ import annotations

import argparse
import hashlib
import json
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
        # Do not even enumerate the sealed Indian folder before its phase exists.
        raise NotImplementedError("Indian sealed-case scoring is gated on Phase 10 acceptance")


if __name__ == "__main__":
    main()
