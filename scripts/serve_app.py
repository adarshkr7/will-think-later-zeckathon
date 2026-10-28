"""Launch Streamlit with its output path and server settings from YAML."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari.config import Config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args()
    config = Config(args.config)
    settings = config.section("app_config")
    manifest = config.path("app_manifest")
    if not manifest.is_file() or not manifest.resolve().is_relative_to(config.path("outputs").resolve()):
        raise RuntimeError("Build the configured output bundle first")
    environment = dict(os.environ, PRAHARI_APP_MANIFEST=str(manifest))
    command = [sys.executable, "-m", "streamlit", "run", str(config.path("app_entrypoint")),
               "--server.headless", "true", "--browser.gatherUsageStats", "false",
               "--server.address", settings["address"], "--server.port", str(settings["port"])]
    raise SystemExit(subprocess.call(command, cwd=config.root, env=environment))


if __name__ == "__main__":
    main()
