"""Prepare official benchmarks and run development CV; never open hold-outs."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import pandas as pd
from sklearn.base import clone

from prahari.config import Config
from prahari.data.benchmark_store import prepare_training
from prahari.data.firewall import write_real_table
from prahari.data.uci import sha256_file
from prahari.eval.metrics import benchmark_metrics, calibration_table
from prahari.eval.plots import calibration_plot
from prahari.eval.seal import code_fingerprint
from prahari.features.harmonize import harmonize
from prahari.models.benchmark import nested_development

LOG = logging.getLogger(__name__)
META = {"target", "is_synthetic", "source_url", "horizon_file"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--offline", action="store_true", help="Use verified download cache only")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    # A final claim forbids additional development; no implicit reruns after results.
    if config.path("benchmark_ledger").exists():
        raise RuntimeError("Final benchmark was opened; development is locked")
    if config.path("benchmark_lock").exists():
        raise RuntimeError("Benchmark frozen; do not mutate development artifacts")
    settings = config.section("benchmark_config")
    policy = config.section("policy_config")
    mapping = config.section("harmonized_map")
    tables = {name: prepare_training(config, name, offline=args.offline) for name in settings["datasets"]}
    # Check every mapping against actual parsed columns before a costly run.
    for name, table in tables.items():
        harmonize(table, settings["datasets"][name]["source"], mapping, shared_only=True)
    if args.prepare_only:
        LOG.info("Preparation complete; reserved rows and indices remain sealed")
        return
    rows, entries, audits = [], [], {}
    fingerprint = code_fingerprint(config)
    generation = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
    model_directory = config.path("models") / generation
    model_directory.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        tasks = [("full", variant) for variant in [*settings["models"]["imbalance_variants"], "logistic"]]
        if name in settings["hdm"]["datasets"]:
            tasks.append(("harmonized", "none"))
        for representation, variant in tasks:
            run_id = f"{name}_{representation}_{variant}"
            artifact = model_directory / f"{run_id}.joblib"
            result_path = artifact.with_suffix(".development.json")
            if representation == "full":
                X = table.drop(columns=list(META))
                signs = None
            else:
                X = harmonize(table, settings["datasets"][name]["source"], mapping, shared_only=True)
                signs = [mapping["ratios"][column]["monotone"] for column in X]
            identity = {"fingerprint": fingerprint, "training_sha256": sha256_file(
                config.path("benchmark_training_dir") / f"{name}.parquet")}
            if artifact.exists() and result_path.exists():
                saved = json.loads(result_path.read_text(encoding="utf-8"))
                if saved["identity"] != identity:
                    raise ValueError(f"Stale development artifact {run_id}; use a fresh configured models directory")
                if saved["artifact_sha256"] != sha256_file(artifact):
                    raise ValueError("Model cache integrity failure")
                rows.extend(saved["rows"])
                audits[run_id] = saved["folds"]
                entries.append(saved["entry"])
                calibration = pd.DataFrame(saved["calibration"])
                write_real_table(calibration, config.path("benchmark_plots") / f"{run_id}.csv")
                plot_path = config.path("benchmark_plots") / f"{run_id}.png"
                if not plot_path.exists():
                    calibration_plot(calibration, plot_path)
                LOG.info("Reused development artifact %s", run_id)
                continue
            LOG.info("Starting %s rows=%s features=%s dates_imputed=0", run_id, len(X), len(X.columns))
            result = nested_development(X, table.target.to_numpy(), settings, config.seed,
                                        variant, source=name, monotone=signs)
            metrics = benchmark_metrics(table.target.to_numpy(), result.probabilities,
                                        settings["metrics"], policy, config.seed)
            entry = {"dataset": name, "representation": representation, "variant": variant,
                     "horizon_quarters": settings["datasets"][name]["horizon_quarters"],
                     "artifact": str(artifact.relative_to(config.root)).replace("\\", "/")}
            task_rows = [{**metrics, **{k: v for k, v in entry.items() if k != "artifact"},
                          "evaluation_dataset": name, "evaluation_split": "nested_outer_oof",
                          "is_transfer": 0}]
            # Transfer development uses only Taiwan's unsealed training complement.
            if representation == "harmonized":
                target = tables["taiwan"]
                target_X = harmonize(target, "taiwan", mapping, shared_only=True)
                # Taiwan ratios are normalized: Polish absolute ECDF cutoffs do not apply.
                # Fit only an unlabelled target-country training reference, never hold-out rows.
                result.model.transfer_preprocessor = clone(result.model.pipeline.named_steps["preprocess"]).fit(target_X)
                transfer = benchmark_metrics(target.target.to_numpy(), result.model.predict_transfer(target_X),
                                             settings["metrics"], policy, config.seed)
                task_rows.append({**transfer, **{k: v for k, v in entry.items() if k != "artifact"},
                                  "evaluation_dataset": "taiwan", "evaluation_split": "transfer_development",
                                  "is_transfer": 1})
            joblib.dump(result.model, artifact)
            calibration = calibration_table(table.target.to_numpy(), result.probabilities, settings["metrics"]["ece_bins"])
            write_real_table(calibration, config.path("benchmark_plots") / f"{run_id}.csv")
            # Render the same persisted values used by reports and the future app.
            calibration_plot(pd.read_csv(config.path("benchmark_plots") / f"{run_id}.csv"),
                             config.path("benchmark_plots") / f"{run_id}.png")
            result_path.write_text(json.dumps({"identity": identity, "artifact_sha256": sha256_file(artifact),
                                               "entry": entry, "rows": task_rows, "folds": result.folds,
                                               "calibration": calibration.astype(object).where(pd.notna(calibration), None).to_dict(orient="records")}, indent=2),
                                    encoding="utf-8")
            rows.extend(task_rows)
            entries.append(entry)
            audits[run_id] = result.folds
            write_real_table(pd.DataFrame(rows), config.path("benchmark_development_metrics"))
    write_real_table(pd.DataFrame(rows), config.path("benchmark_development_metrics"))
    config.path("benchmark_model_manifest").write_text(json.dumps(entries, indent=2), encoding="utf-8")
    config.path("benchmark_audit").write_text(json.dumps(audits, indent=2), encoding="utf-8")
    LOG.info("Development complete: metric_rows=%s; final hold-outs unopened", len(rows))


if __name__ == "__main__":
    main()
