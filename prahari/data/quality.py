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
            if key == "public_date" and name == "financial_evidence" and row["date_is_imputed"] == 1:
                continue
            if row[key] is None:
                raise ValueError(f"{name}: verified row lacks {key}")
        if name != "trading_calendar" and row["public_date"] is not None and row["public_date"] < row["period_end"]:
            raise ValueError(f"{name}: public date precedes observation period")
        if name == "events":
            # Event verification and matching metadata have separate acceptance
            # checks. Human-verified dates do not license guessed classifications.
            if row["name"] is None:
                raise ValueError("Verified events need a company name")
            dates = [row[key] for key in ("first_payment_default_date", "first_D_rating_date", "cirp_admission_date")
                     if row[key] is not None]
            if not dates or row["event_date"] != min(dates):
                raise ValueError("Event date must be the earliest verified candidate date")
        if name == "event_evidence":
            if row["event_type"] not in ("payment_default", "D_rating", "cirp"):
                raise ValueError("Unrecognized event component")
            if any(row[key] is None for key in ("verified_on", "verification_method", "event_rule_version")):
                raise ValueError("Verified event evidence needs review provenance")
            if row["event_type"] == "D_rating" and row["cured_before_final_default"] is None:
                raise ValueError("Verified D evidence needs an explicit cure determination")
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
        if name == "entities" and any(row[key] is None for key in ("name", "symbols", "sector", "is_financial")):
            raise ValueError("Verified entity metadata lacks classification/identity evidence")
        if name == "peer_survival":
            if any(row[key] is None for key in ("matched_to", "nondefault_start", "nondefault_through")):
                raise ValueError("Survival evidence needs a complete sourced window")
            if row["nondefault_start"] > row["nondefault_through"]:
                raise ValueError("Invalid survival window")
        if name == "security_crosswalk" and (row["exchange"] not in ("nse", "bse") or row["exchange_code"] is None):
            raise ValueError("Invalid sourced exchange identity mapping")
        if name == "financial_evidence":
            annual = settings["tables"]["annual_financials"]
            allowed = annual["numeric"] + ["auditor_opinion", "going_concern_flag", "caro_default_flag", "caro_fraud_flag"]
            if row["field"] not in allowed or row["basis"] not in settings["validation"]["fiscal_basis"]:
                raise ValueError("Unrecognized financial evidence field/basis")
            if row["fy_end"] != row["period_end"] or row["source_page"] is None or row["source_page"] < 1 or row["source_page"] % 1:
                raise ValueError("Financial evidence needs a fiscal period and document page")
            if row["source_period_end"] is None or row["source_period_end"] < row["fy_end"]:
                raise ValueError("Comparative values need the source report's reporting period")
            if row["unit"] is None or row["publication_kind"] not in ("results", "annual_report"):
                raise ValueError("Financial evidence needs explicit units and publication kind")
            if (row["numeric_value"] is None) == (row["text_value"] is None):
                raise ValueError("Verified evidence must contain exactly one numeric/text value")
            if row["field"] == "auditor_opinion":
                if row["unit"] != "text" or row["text_value"] not in settings["validation"]["audit_opinions"]:
                    raise ValueError("Auditor opinion evidence needs a recognized sourced opinion")
            elif row["field"] in ("going_concern_flag", "caro_default_flag", "caro_fraud_flag"):
                if row["unit"] != "flag" or row["numeric_value"] not in (0, 1):
                    raise ValueError("Audit flags require explicit binary source evidence")
            elif row["field"] == "shares_outstanding":
                if not row["unit"].startswith("shares") or row["numeric_value"] is None:
                    raise ValueError("Outstanding shares need count units")
            elif not row["unit"].startswith("INR") or row["numeric_value"] is None:
                raise ValueError("Monetary financial evidence needs explicit INR denomination")
        if name in ("nbfc_metrics", "shareholding") and any(row[key] is None for key in spec["numeric"]):
            raise ValueError("Incomplete numerical row must set needs_verification=1")
        if name == "share_counts" and (row["shares_outstanding"] is None or row["shares_outstanding"] <= 0):
            raise ValueError("Shareholding share counts need a positive sourced count")
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
    from prahari.data.events import validate_event_evidence
    from prahari.data.manual import read_manual
    validate_event_evidence(read_manual(config, "events"), read_manual(config, "event_evidence"),
                            config.section("india_config")["events"])
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


def accounting_from_fields(table: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    """Audit latest known statement triplets; incomplete evidence is reported."""
    fields = table.loc[table.field.isin(["total_assets", "total_liabilities", "equity"])].copy()
    fields = fields.sort_values("public_date").drop_duplicates(["entity_id", "period_end", "basis", "field"], keep="last")
    if fields.empty:
        return accounting_coverage(pd.DataFrame(), tolerance)
    keys = ["entity_id", "period_end", "basis"]
    wide = fields.pivot(index=keys, columns="field", values="value").reset_index()
    metadata = fields.groupby(keys, as_index=False).agg(source_doc=("source_doc", lambda values: ";".join(sorted(set(values)))),
                                                       is_synthetic=("is_synthetic", "max"))
    wide = wide.merge(metadata, on=keys, validate="one_to_one")
    for field in ("total_assets", "total_liabilities", "equity"):
        if field not in wide:
            wide[field] = float("nan")
    return accounting_coverage(wide, tolerance)
