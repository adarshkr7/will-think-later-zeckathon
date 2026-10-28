"""Field-level filing dates, lag flags and restatement-safe financial access."""

from __future__ import annotations

import logging

import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.manual import read_manual

LOG = logging.getLogger(__name__)
COLUMNS = ["entity_id", "field", "value", "basis", "period_end", "public_date", "source_doc",
           "source_page", "unit", "missing_reason", "date_is_imputed", "needs_verification", "is_synthetic"]


def normalize_financials(table: pd.DataFrame, settings: dict, lags: dict, fields: list[str]) -> pd.DataFrame:
    """Date each field independently; annual-only fields never inherit results dates.

    Missing values remain unknown. An unverified source row remains quarantined;
    normalizing it does not turn observed numbers into verified evidence.
    """
    rows = []
    annual_only = set(settings["financials"]["annual_only_fields"])
    for record in table.to_dict(orient="records"):
        end = pd.to_datetime(record["fy_end"], utc=True)
        if pd.isna(end):
            raise ValueError("Financial observations need a fiscal period end")
        for field in fields:
            annual = field in annual_only
            date_column = "annual_report_public_date" if annual else "results_public_date"
            publication = pd.to_datetime(record[date_column], utc=True)
            if pd.isna(publication) and not annual:
                publication = pd.to_datetime(record["annual_report_public_date"], utc=True)
            imputed = int(pd.isna(publication))
            if imputed:
                lag = lags["annual_report_lag_days" if annual else "results_lag_days"]
                publication = end + pd.Timedelta(days=lag)
            if publication < end:
                raise ValueError("Publication precedes financial period")
            value = record[field]
            rows.append({"entity_id": record["entity_id"], "field": field, "value": value,
                         "basis": record["basis"], "period_end": end, "public_date": publication,
                         "source_doc": record["source_doc"], "date_is_imputed": max(imputed, int(record.get("date_is_imputed", 0))),
                         "source_page": None, "unit": "shares" if field == "shares_outstanding" else "canonical_manual_input",
                         "missing_reason": "unverified_source_row" if record["needs_verification"] else ("missing_value" if pd.isna(value) else ""),
                         "needs_verification": int(bool(record["needs_verification"]) or pd.isna(value)),
                         "is_synthetic": record["is_synthetic"]})
    result = pd.DataFrame(rows, columns=COLUMNS)
    LOG.info("Financial normalization rows=%s dates_imputed=%s missing=%s", len(result),
             result.date_is_imputed.sum(), result.value.isna().sum())
    return result


def financial_table(config: Config) -> pd.DataFrame:
    spec = config.section("manual_config")["tables"]["annual_financials"]
    fields = spec["numeric"] + ["auditor_opinion", "going_concern_flag", "caro_default_flag", "caro_fraud_flag"]
    settings = config.section("india_config")
    wide = normalize_financials(read_manual(config, "annual_financials"), settings, config.base["dates"], fields)
    evidence = normalize_evidence(read_manual(config, "financial_evidence"), settings, config.base["dates"])
    return combine_financial_evidence(wide, evidence)


def financials_as_of(config: Config, t: str | pd.Timestamp) -> pd.DataFrame:
    return as_of(financial_table(config), t)


def normalize_evidence(table: pd.DataFrame, settings: dict, lags: dict) -> pd.DataFrame:
    """Keep verification per field; standardize explicitly reported units only.

    Unit multipliers are exact count conversions from the source's printed
    denomination to INR or individual shares. Unknown units never imply INR.
    """
    rows = []
    multipliers = settings["financials"]["unit_multipliers"]
    annual_only = set(settings["financials"]["annual_only_fields"])
    for record in table.to_dict(orient="records"):
        end = pd.to_datetime(record["fy_end"], utc=True)
        if pd.isna(end):
            raise ValueError("Field evidence needs a fiscal period")
        annual = record["field"] in annual_only or record["publication_kind"] == "annual_report"
        publication = pd.to_datetime(record["public_date"], utc=True)
        imputed = int(pd.isna(publication))
        if imputed:
            report_end = pd.to_datetime(record["source_period_end"], utc=True)
            if pd.isna(report_end) or report_end < end:
                raise ValueError("Cannot date comparative values without the source reporting period")
            publication = report_end + pd.Timedelta(days=lags["annual_report_lag_days" if annual else "results_lag_days"])
        if publication < end:
            raise ValueError("Financial evidence publication precedes period end")
        unit = record["unit"]
        value = record["text_value"] if unit == "text" else record["numeric_value"]
        reason = ""
        if unit not in multipliers:
            value, reason = float("nan"), "unknown_source_unit"
        elif pd.isna(value):
            reason = "missing_value"
        elif unit != "text":
            value *= multipliers[unit]
        if record["needs_verification"]:
            reason = "unverified_field_evidence"
        rows.append({"entity_id": record["entity_id"], "field": record["field"], "value": value,
                     "basis": record["basis"], "period_end": end, "public_date": publication,
                     "source_doc": record["source_doc"], "source_page": record["source_page"],
                     "unit": (unit if unit in ("text", "flag") else ("shares" if str(unit).startswith("shares") else "INR")) if unit in multipliers else None,
                     "missing_reason": reason, "date_is_imputed": max(imputed, int(record["date_is_imputed"])),
                     "needs_verification": int(bool(reason)), "is_synthetic": record["is_synthetic"]})
    return pd.DataFrame(rows, columns=COLUMNS)


def combine_financial_evidence(wide: pd.DataFrame, evidence: pd.DataFrame) -> pd.DataFrame:
    result = pd.concat([wide, evidence], ignore_index=True)
    keys = ["entity_id", "field", "period_end", "basis", "public_date"]
    known = result.loc[result.needs_verification.eq(0)]
    if not known.empty and known.groupby(keys).value.nunique().gt(1).any():
        raise ValueError("Contradictory financial values at the same publication date")
    # Verified field-specific evidence can supersede a quarantined wide field;
    # it does not upgrade any other field from the incomplete source row.
    result = result.sort_values("needs_verification", ascending=False).drop_duplicates(keys, keep="last")
    return result.reset_index(drop=True)
