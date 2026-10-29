"""Reconcile extended/quarterly disclosures to exact trailing annual flows."""

from __future__ import annotations

from decimal import Decimal
import logging

import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.downloads import CachedDownloader
from prahari.data.firewall import write_real_table
from prahari.data.manual import read_manual
from prahari.data.quality import validate_table
from prahari.data.uci import sha256_file

LOG = logging.getLogger(__name__)


def validate_annual_cover(components: list[dict], end: str) -> None:
    """Check exact interval algebra, not proportional annualisation.

    Financial flows are additive over disjoint intervals. A signed combination
    must have weight one on every day of the trailing calendar year and zero
    everywhere else. Extended reports therefore require sourced subperiods.
    """
    finish = pd.to_datetime(end, utc=True) + pd.Timedelta(days=1)
    start = finish - pd.DateOffset(years=1)
    intervals = []
    for row in components:
        coefficient = row["coefficient"]
        first = pd.to_datetime(row["period_start"], utc=True)
        last = pd.to_datetime(row["period_end"], utc=True) + pd.Timedelta(days=1)
        if coefficient not in (-1, 1) or pd.isna(first) or pd.isna(last) or first >= last:
            raise ValueError("Invalid signed financial interval")
        intervals.append((first, last, coefficient))
    boundaries = sorted({start, finish, *(point for first, last, _ in intervals for point in (first, last))})
    for left, right in zip(boundaries, boundaries[1:]):
        weight = sum(coefficient for first, last, coefficient in intervals if first <= left and right <= last)
        expected = int(start <= left and right <= finish)
        if weight != expected:
            raise ValueError("Intervals do not cover exactly one trailing year")


def reconcile_annual_flows(table: pd.DataFrame, rules: list[dict], units: dict,
                           t: str | pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Use publication-visible, reviewed operands and retain every source.

    See validate_annual_cover for interval additivity. No label, event date or
    model output enters this calculation. Missing operands remain unavailable.
    """
    known = as_of(table, t)
    rows, audit = [], []
    for rule in rules:
        end = rule["fy_end"]
        for field in rule["fields"]:
            operands, missing = [], []
            for component in rule["components"]:
                selected = known.loc[known.series_id.eq(component["series_id"])
                                     & known.entity_id.eq(rule["entity_id"])
                                     & known.basis.eq(rule["basis"]) & known.field.eq(field)]
                if selected.empty:
                    missing.append(component["series_id"])
                    continue
                if len(selected) != 1:
                    raise ValueError("Ambiguous financial interval operand")
                operands.append({**selected.iloc[0].to_dict(), "coefficient": component["coefficient"]})
            if missing:
                LOG.warning("Annual flow unavailable entity=%s period=%s field=%s missing=%s",
                            rule["entity_id"], end, field, missing)
                audit.append({"entity_id": rule["entity_id"], "period_end": end, "field": field,
                              "numeric_value": float("nan"), "missing_reason": "missing_visible_interval_operand",
                              "source_doc": ";".join(str(row["source_doc"]) for row in operands),
                              "public_date": max((row["public_date"] for row in operands), default=pd.NaT),
                              "needs_verification": 1, "is_synthetic": int(table.is_synthetic.eq(1).any())})
                continue
            validate_annual_cover(operands, end)
            if any(pd.isna(row["numeric_value"]) for row in operands):
                raise ValueError("Verified interval lacks a finite financial value")
            value = sum(Decimal(str(row["coefficient"])) * Decimal(str(row["numeric_value"]))
                        * Decimal(str(units[row["unit"]])) for row in operands)
            if not value.is_finite():
                raise ValueError("Nonfinite annual interval calculation")
            publication = max(row["public_date"] for row in operands)
            source = ";".join(f"{row['source_doc']}#page={int(row['source_page'])}" for row in operands)
            synthetic = int(any(row["is_synthetic"] for row in operands))
            row = {"entity_id": rule["entity_id"], "fy_end": end, "period_end": end,
                   "source_period_end": max(pd.to_datetime(item["source_period_end"], utc=True) for item in operands).date().isoformat(),
                   "basis": rule["basis"], "field": field, "numeric_value": float(value), "text_value": None,
                   "unit": "INR", "publication_kind": "annual_report", "public_date": publication.isoformat(),
                   "source_doc": source, "source_page": operands[0]["source_page"],
                   "date_is_imputed": max(item["date_is_imputed"] for item in operands),
                   "needs_verification": 0, "is_synthetic": synthetic}
            rows.append(row)
            audit.append({"entity_id": row["entity_id"], "period_end": end, "field": field,
                          "numeric_value": row["numeric_value"], "missing_reason": "",
                          "source_doc": source, "public_date": publication,
                          "needs_verification": 0, "is_synthetic": synthetic})
    return pd.DataFrame(rows), pd.DataFrame(audit)


def import_reconciled_flows(config: Config) -> None:
    if config.path("preregistration_lock").exists():
        raise RuntimeError("Financial inputs are registered; amendment required")
    settings = config.section("financial_reconciliations_config")
    client = CachedDownloader(config)
    try:
        for source in settings["sources"]:
            path = client.fetch(source["source"], source["url"], source["filename"], offline=True)
            if sha256_file(path) != source["sha256"]:
                raise ValueError("Reviewed financial interval source changed")
    finally:
        client.close()
    table = read_manual(config, "financial_intervals")
    validate_table(table, "financial_intervals", config.section("manual_config"))
    sources = {source["key"]: source for source in settings["sources"]}
    for row in table.to_dict(orient="records"):
        if row["source_key"] not in sources or row["source_doc"] != sources[row["source_key"]]["url"]:
            raise ValueError("Financial interval lacks a receipt-checked original source")
    fresh, audit = reconcile_annual_flows(table, settings["rules"],
                                         config.section("india_config")["financials"]["unit_multipliers"],
                                         pd.Timestamp.now(tz="UTC"))
    destination = config.path("manual") / "financial_evidence.csv"
    current = pd.read_csv(destination)
    keys = ["entity_id", "fy_end", "basis", "field", "source_doc", "source_page"]
    combined = pd.concat([current, fresh], ignore_index=True).drop_duplicates()
    if combined.duplicated(keys).any():
        raise ValueError("Reconciled flow conflicts with existing evidence")
    write_real_table(combined, destination)
    write_real_table(audit, config.path("financial_reconciliations"))
    LOG.info("Reconciled annual flows=%s dates_imputed=%s missing=%s", len(fresh),
             fresh.date_is_imputed.sum() if len(fresh) else 0, audit.needs_verification.sum())
