"""Package the output-only demo after engineering checks, without private data."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
import sys
import zipfile

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from prahari.config import Config
from prahari.data.feature_lineage import feature_input_fingerprint, verify_feature_receipt
from prahari.data.firewall import write_real_table
from prahari.data.uci import sha256_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    settings = config.section("delivery_config")
    tests = json.loads(config.path("test_summary").read_text(encoding="utf-8"))
    ui = json.loads(config.path("ui_validation").read_text(encoding="utf-8"))
    if tests["status"] != "passed" or not ui["passed"]:
        raise ValueError("Demo engineering checks have not passed")
    trace = pd.read_csv(config.path("report_trace"))
    for row in trace.to_dict(orient="records"):
        source = (config.root / row["source_path"]).resolve()
        if not source.is_relative_to(config.path("outputs").resolve()):
            raise ValueError("Report source escapes the output bundle")
        if sha256_file(source) != row["sha256"]:
            raise ValueError("Generated report source hash changed")
    checks = pd.read_csv(config.path("panel_acceptance"))
    app = json.loads(config.path("app_manifest").read_text(encoding="utf-8"))
    inputs = feature_input_fingerprint(config)
    epoch = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    dates = config.section("feature_config")["dates"]
    quarters = pd.date_range(dates["first_quarter"], dates["last_quarter"], freq="QE-MAR")
    lineage = []
    for arena in config.base["pipeline"]["arenas"]:
        if arena not in {"P", "U"}:
            raise ValueError("Unexpected public feature arena")
        selected = config.base["pipeline"]["readiness_universe_dates"] if arena == "U" and app["mode"] == "readiness_only" else None
        for day in pd.to_datetime(selected) if selected else quarters:
            artifact = config.path("feature_cache") / arena / f"{day:%Y-%m-%d}.parquet"
            verify_feature_receipt(config, artifact, inputs)
            lineage.append({"arena": arena, "quarter": day.date().isoformat(),
                "artifact_sha256": sha256_file(artifact), "source_epoch_sha256": epoch,
                "verified": 1, "is_synthetic": 0})
    if feature_input_fingerprint(config) != inputs:
        raise ValueError("Public inputs changed during delivery verification")
    lineage_path = (config.root / settings["feature_lineage_audit"]).resolve()
    if not lineage_path.is_relative_to(config.path("outputs").resolve()):
        raise ValueError("Delivery lineage audit must remain inside outputs")
    write_real_table(pd.DataFrame(lineage), lineage_path)
    paths = {config.root / name for name in settings["files"]}
    manual_paths = set()
    if settings.get("public_manual_tables", False):
        # Explicit public schema names only; never recurse into manual/sealed.
        for name in config.section("manual_config")["tables"]:
            if not name.replace("_", "").isalnum() or "sealed" in name.casefold():
                raise ValueError("Only public manual table names may be packaged")
            manual_paths.add(config.path("manual") / (name + ".csv"))
        paths.update(manual_paths)
    for directory in settings["directories"]:
        folder = (config.root / directory).resolve()
        if not folder.is_relative_to(config.root) or folder == config.root:
            raise ValueError("Unsafe delivery directory")
        paths.update(path for path in folder.rglob("*") if path.is_file())
    paths = {path for path in paths if path != config.path("delivery_manifest")
             and not set(path.relative_to(config.root).parts).intersection(settings["excluded_parts"])
             and path.suffix not in settings["excluded_suffixes"]}
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(config.root):
            raise ValueError("Delivery inputs cannot follow external links")
        relative = path.relative_to(config.root)
        if (relative.parts[0] not in {"app", "prahari", "scripts", "configs", "outputs", "docs", "tests"}
                and len(relative.parts) != 1 and path not in manual_paths):
            raise ValueError("Unexpected delivery input")
        if not path.is_file():
            raise FileNotFoundError(path)
    manifest = {"mode": app["mode"], "created_at": pd.Timestamp.now(tz="UTC").isoformat(),
                "scientific_panel_accepted": bool(checks.passed.eq(1).all()),
                "failed_panel_checks": checks.loc[checks.passed.ne(1), "check"].tolist(),
                "engineering_tests": tests, "ui_validation": ui,
                "verified_feature_artifacts": len(lineage), "feature_source_epoch_sha256": epoch,
                "archive": settings["archive"], "is_synthetic": 0,
                "files": {path.relative_to(config.root).as_posix(): sha256_file(path) for path in sorted(paths)}}
    config.path("delivery_manifest").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    paths.add(config.path("delivery_manifest"))
    destination = (config.root / settings["archive"]).resolve()
    if not destination.is_relative_to(config.root):
        raise ValueError("Delivery archive must remain inside the project")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".partial")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path, path.relative_to(config.root).as_posix())
    temporary.replace(destination)
    destination.with_suffix(destination.suffix + ".sha256").write_text(sha256_file(destination) + "\n", encoding="utf-8")
    logging.info("Offline archive=%s files=%s mode=%s scientific_panel_accepted=%s",
                 destination, len(paths), manifest["mode"], manifest["scientific_panel_accepted"])


if __name__ == "__main__":
    main()
