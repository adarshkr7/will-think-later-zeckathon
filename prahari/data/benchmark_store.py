"""Create sealed benchmark partitions without exposing their membership."""

from __future__ import annotations

import hashlib
import json
import logging

import pandas as pd
from sklearn.model_selection import train_test_split

from prahari.config import Config
from prahari.data.firewall import assert_real
from prahari.data.uci import download, load_dataset, sha256_file

LOG = logging.getLogger(__name__)


def prepare_training(config: Config, name: str, *, offline: bool = False) -> pd.DataFrame:
    """Idempotent preparation. Subsequent development never reads sealed files."""
    folder = config.path("benchmark_training_dir")
    path = folder / f"{name}.parquet"
    metadata_path = folder / f"{name}.json"
    spec = config.section("benchmark_config")
    raw_path = download(config, spec["datasets"][name]["source"], offline=offline)
    identity = {"source_sha256": sha256_file(raw_path), "seed": config.seed,
                "holdout_frac": spec["split"]["holdout_frac"]}
    if path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if any(metadata.get(k) != v for k, v in identity.items()):
            raise ValueError("Split configuration changed; refuse to recreate a reserved hold-out")
        if metadata["training_sha256"] != sha256_file(path):
            raise ValueError("Training partition integrity failure")
        return pd.read_parquet(path).set_index("row_id")
    seal = config.path("benchmark_seal_dir")
    if (seal / f"holdout_{name}.json").exists() or (seal / f"holdout_{name}.parquet").exists():
        raise ValueError("Sealed split already exists; do not regenerate its training complement")
    table = load_dataset(config, name, offline=offline)
    assert_real(table)
    train_ids, reserved_ids = train_test_split(table.index.to_numpy(), test_size=identity["holdout_frac"],
                                              stratify=table.target, random_state=config.seed)
    # This is the initial write, not a read or inspection of sealed membership.
    seal.mkdir(parents=True, exist_ok=True)
    membership = json.dumps(sorted(int(i) for i in reserved_ids), separators=(",", ":"))
    seal_payload = {"indices": json.loads(membership),
                    "sha256": hashlib.sha256(membership.encode()).hexdigest(), **identity}
    (seal / f"holdout_{name}.json").write_text(json.dumps(seal_payload), encoding="utf-8")
    table.loc[reserved_ids].reset_index().to_parquet(seal / f"holdout_{name}.parquet", index=False)
    folder.mkdir(parents=True, exist_ok=True)
    table.loc[train_ids].reset_index().to_parquet(path, index=False)
    metadata_path.write_text(json.dumps({**identity, "training_sha256": sha256_file(path)}, indent=2),
                             encoding="utf-8")
    LOG.info("Prepared %s training rows=%s; reserved partition sealed; dates_imputed=0", name, len(train_ids))
    return table.loc[train_ids]
