"""Configured cached pipeline; readiness builds retain every production gate."""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config
from prahari.models.development_cache import restore_development_cache


def run(config, module, *arguments, allow_failure=False):
    command = [sys.executable, "-m", module, "--config", str(config.file), *arguments]
    result = subprocess.run(command, cwd=config.root)
    if result.returncode and not allow_failure:
        raise subprocess.CalledProcessError(result.returncode, command)
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--readiness", action="store_true", help="Build an honestly labelled incomplete-data demo without registration or replay")
    args = parser.parse_args()
    config = Config(args.config)
    config.setup_logging()
    stages = config.base["pipeline"]
    registered = config.path("preregistration_lock").exists()
    reuse_development = args.readiness and stages.get("readiness_benchmark_cache", {}).get("enabled", False)
    if reuse_development:
        restore_development_cache(config)
        logging.info("Readiness build reuses the verified complete foreign development epoch; final data remain unopened")
    if not config.path("benchmark_lock").exists() and not registered and not reuse_development:
        options = ["--offline"] if args.offline else []
        if args.prepare_only:
            options.append("--prepare-only")
        run(config, stages["benchmark"], *options)
    if args.prepare_only:
        return
    if not registered:
        for stage in stages["preparation"]:
            options = ["--offline"] if args.offline and stage.get("offline") else []
            run(config, stage["module"], *options, *stage.get("arguments", []))
    validation = run(config, stages["data_validation"], allow_failure=True)
    if validation and not args.readiness:
        run(config, stages["bundle"])
        run(config, stages["report"])
        raise RuntimeError("Production pipeline stopped at panel acceptance; see outputs/panel_acceptance.csv and docs/DATA_REQUESTS.md")
    if not registered:
        for arena in stages["arenas"]:
            dates = (stages["readiness_universe_dates"] or [None]) if args.readiness and arena == "U" else [None]
            for day in dates:
                options = ["--arena", arena, *(["--date", day] if day else [])]
                run(config, stages["universe"], *options)
                run(config, stages["features"], *options)
    if not args.readiness:
        if not registered:
            run(config, stages["registration"])
            if stages["auto_commit_registration"]:
                relative = str(config.path("preregistration_lock").relative_to(config.root)).replace("\\", "/")
                subprocess.run(["git", "add", "--", relative], cwd=config.root, check=True)
                subprocess.run(["git", "commit", "-m", "phase 4: freeze Indian preregistration before replay", "--", relative], cwd=config.root, check=True)
        for arena in stages["arenas"]:
            run(config, stages["replay"], "--arena", arena)
        run(config, stages["evaluation"])
        if config.section("diagnostics_config")["enabled_after_registration"]:
            run(config, stages["diagnostics"])
    else:
        logging.info("Readiness mode: no registration, replay, Indian performance evaluation or sealed opening")
    run(config, stages["tests"])
    run(config, stages["bundle"])
    run(config, stages["ui_validation"])
    run(config, stages["report"])


if __name__ == "__main__":
    main()
