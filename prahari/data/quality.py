"""Strict manual input templates and schema validation. No guessed values."""

from __future__ import annotations

import csv
from datetime import date
import logging
from typing import Literal

import pandas as pd
from pydantic import ConfigDict, create_model

from prahari.config import Config

LOG = logging.getLogger(__name__)


def initialize_templates(config: Config) -> None:
    """Write headers only. Existing human inputs are never overwritten."""
    folder = config.path("manual")
    folder.mkdir(parents=True, exist_ok=True)
    for name, spec in config.section("manual_config")["tables"].items():
        path = folder / f"{name}.csv"
        if not path.exists():
            with path.open("x", newline="", encoding="utf-8") as stream:
                csv.writer(stream).writerow(spec["columns"])
        LOG.info("Manual template %s ready; no company records generated", name)


def validate_table(table: pd.DataFrame, name: str, settings: dict) -> dict:
    spec = settings["tables"][name]
    if set(table.columns) != set(spec["columns"]):
        raise ValueError(f"{name}: missing/extra columns in manual CSV")
    fields = {}
    for column in spec["columns"]:
        if column in spec["dates"]:
            kind = date
        elif column in spec["numeric"]:
            kind = float
        elif column in spec["flags"]:
            kind = Literal[0, 1]
        else:
            kind = str
        fields[column] = (kind | None, None)
    schema = create_model(f"Manual_{name}", __config__=ConfigDict(extra="forbid", allow_inf_nan=False), **fields)
    verified = pending = imputed = 0
    for raw in table.to_dict(orient="records"):
        values = {key: (None if pd.isna(value) or value == "" else value) for key, value in raw.items()}
        # CSV flags arrive as strings; parse only exact 0/1 representations.
        for key in spec["flags"]:
            if values[key] in ("0", "1"):
                values[key] = int(values[key])
        row = schema.model_validate(values).model_dump()
        if row["is_synthetic"] != 0:
            raise ValueError(f"{name}: synthetic rows are forbidden in manual inputs")
        if row["needs_verification"] not in (0, 1) or row["date_is_imputed"] not in (0, 1):
            raise ValueError(f"{name}: verification and date flags are required")
        imputed += row["date_is_imputed"]
        if row["needs_verification"]:
            pending += 1
            continue
        for key in ("entity_id", "period_end", "public_date", spec["source"]):
            if row[key] is None:
                raise ValueError(f"{name}: verified row lacks {key}")
        if row["public_date"] < row["period_end"]:
            raise ValueError(f"{name}: public date precedes observation period")
        if name == "events":
            dates = [row[key] for key in ("first_payment_default_date", "first_D_rating_date", "cirp_admission_date")
                     if row[key] is not None]
            if not dates or row["event_date"] != min(dates):
                raise ValueError("Event date must be the earliest verified candidate date")
        if name == "annual_financials":
            if row["basis"] not in settings["validation"]["fiscal_basis"]:
                raise ValueError("Unrecognized accounting basis")
            if row["auditor_opinion"] is not None and row["auditor_opinion"] not in settings["validation"]["audit_opinions"]:
                raise ValueError("Unrecognized auditor opinion")
            assets, liabilities, equity = (row[key] for key in ("total_assets", "total_liabilities", "equity"))
            if all(value is not None for value in (assets, liabilities, equity)):
                if assets <= 0 or abs(assets - liabilities - equity) / assets > settings["validation"]["accounting_tolerance"]:
                    raise ValueError("Accounting identity outside configured tolerance")
            # Any uncollected financial field requires human verification.
            if any(row[key] is None for key in spec["numeric"]):
                raise ValueError("Incomplete financial row must set needs_verification=1")
        if name == "governance_events" and row["event_type"] not in settings["validation"]["governance_event_types"]:
            raise ValueError("Unrecognized governance event")
        if name == "peers" and not all(row[key] is not None for key in ("matched_to", "sector", "selection_rule_version", "is_stressed_survivor")):
            raise ValueError("Verified peer lacks selection evidence")
        if name in ("nbfc_metrics", "shareholding") and any(row[key] is None for key in spec["numeric"]):
            raise ValueError("Incomplete numerical row must set needs_verification=1")
        verified += 1
    missing = table.isna().sum().loc[lambda series: series.gt(0)].to_dict()
    LOG.info("%s rows=%s dates_imputed=%s missing=%s verified=%s pending=%s",
             name, len(table), imputed, missing, verified, pending)
    return {"table": name, "rows": len(table), "verified": verified, "pending": pending,
            "dates_imputed": imputed, "is_synthetic": 0}


def validate_manual(config: Config) -> pd.DataFrame:
    settings = config.section("manual_config")
    rows = []
    for name in settings["tables"]:
        path = config.path("manual") / f"{name}.csv"
        table = pd.read_csv(path, dtype=str)
        rows.append(validate_table(table, name, settings))
    return pd.DataFrame(rows)


def accounting_coverage(table: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    """Report missing inputs and accounting residuals, including unresolved rows."""
    columns = ["entity_id", "period_end", "basis", "total_assets", "total_liabilities", "equity",
               "identity_relative_error", "identity_status", "source_doc", "is_synthetic"]
    rows = []
    for record in table.to_dict(orient="records"):
        values = [record[key] for key in ("total_assets", "total_liabilities", "equity")]
        if any(pd.isna(value) for value in values):
            error, status = float("nan"), "missing_inputs"
        elif values[0] <= 0:
            error, status = float("nan"), "invalid_assets"
        else:
            error = abs(values[0] - values[1] - values[2]) / values[0]
            status = "pass" if error <= tolerance else "fail"
        rows.append({**{key: record[key] for key in columns if key in record},
                     "identity_relative_error": error, "identity_status": status})
    return pd.DataFrame(rows, columns=columns)
