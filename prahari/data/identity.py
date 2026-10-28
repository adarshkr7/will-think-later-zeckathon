"""Explicit sourced identity reconciliation, without fuzzy-name matching."""

from __future__ import annotations

import pandas as pd

from prahari.config import Config
from prahari.data.events import validate_event_evidence
from prahari.data.firewall import write_real_table
from prahari.data.manual import read_manual
from prahari.data.quality import validate_table


def alias_map(evidence: pd.DataFrame) -> dict[str, str]:
    """Accept only explicit, unique internal-key to sourced ISIN mappings.

    Replacing an internal collection key does not alter any observation's
    publication date. Dated exchange crosswalks remain separate as-of inputs.
    """
    known = evidence.loc[evidence.needs_verification.eq(0)]
    if known.alias.duplicated().any():
        raise ValueError("Ambiguous identity alias")
    if not known.entity_id.astype(str).str.fullmatch(r"IN[A-Z0-9]{10}").all():
        raise ValueError("Canonical identity must be a sourced Indian ISIN")
    if not known.alias.astype(str).str.fullmatch(r"CASE_\d+").all():
        raise ValueError("Only explicit internal collection keys can be migrated")
    return dict(zip(known.alias, known.entity_id, strict=True))


def remap_references(table: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Replace declared entity/matching keys only, preserving all data and dates."""
    result = table.copy()
    for column in ("entity_id", "matched_to"):
        if column in result:
            result[column] = result[column].replace(mapping)
    return result


def apply_identity_aliases(config: Config) -> pd.DataFrame:
    """Validate every affected table before writing; never enumerate sealed data."""
    if config.path("preregistration_lock").exists():
        raise RuntimeError("Identity membership is registered; amendment required")
    settings = config.section("manual_config")
    aliases = read_manual(config, "entity_aliases")
    mapping = alias_map(aliases)
    tables = {}
    changed = []
    for name, spec in settings["tables"].items():
        original = read_manual(config, name)
        updated = remap_references(original, mapping)
        if name == "events" and updated.entity_id.duplicated().any():
            raise ValueError("Identity migration would merge distinct event records")
        validate_table(updated, name, settings)
        tables[name] = updated
        if not updated.equals(original):
            changed.append(name)
    validate_event_evidence(tables["events"], tables["event_evidence"], config.section("india_config")["events"])
    for name in changed:
        frame = tables[name]
        for field in settings["tables"][name]["flags"]:
            frame[field] = frame[field].astype("Int64")
        write_real_table(frame, config.path("manual") / f"{name}.csv")
    result = aliases.loc[aliases.needs_verification.eq(0)].copy()
    result["status"] = "resolved_internal_key"
    write_real_table(result, config.path("identity_resolution"))
    return result
