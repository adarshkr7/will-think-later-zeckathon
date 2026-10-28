"""Field-level filing dates, lag flags and restatement-safe financial access."""

from __future__ import annotations

import logging

import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.manual import read_manual

LOG = logging.getLogger(__name__)
COLUMNS = ["entity_id", "field", "value", "basis", "period_end", "public_date", "source_doc",
           "date_is_imputed", "needs_verification", "is_synthetic"]


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
            imputed = int(pd.isna(publication))
            if imputed:
                lag = lags["annual_report_lag_days" if annual else "results_lag_days"]
                publication = end + pd.Timedelta(days=lag)
            if publication < end:
                raise ValueError("Publication precedes financial period")
            value = record[field]
            rows.append({"entity_id": record["entity_id"], "field": field, "value": value,
                         "basis": record["basis"], "period_end": end, "public_date": publication,
                         "source_doc": record["source_doc"], "date_is_imputed": imputed,
                         "needs_verification": int(bool(record["needs_verification"]) or pd.isna(value)),
                         "is_synthetic": record["is_synthetic"]})
    result = pd.DataFrame(rows, columns=COLUMNS)
    LOG.info("Financial normalization rows=%s dates_imputed=%s missing=%s", len(result),
             result.date_is_imputed.sum(), result.value.isna().sum())
    return result


def financial_table(config: Config) -> pd.DataFrame:
    spec = config.section("manual_config")["tables"]["annual_financials"]
    fields = spec["numeric"] + ["auditor_opinion", "going_concern_flag", "caro_default_flag", "caro_fraud_flag"]
    return normalize_financials(read_manual(config, "annual_financials"), config.section("india_config"),
                                config.base["dates"], fields)


def financials_as_of(config: Config, t: str | pd.Timestamp) -> pd.DataFrame:
    return as_of(financial_table(config), t)
