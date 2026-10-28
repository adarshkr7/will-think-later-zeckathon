"""Whitelisted public inputs, loaded once and filtered through as_of per cutoff."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from prahari.config import Config
from prahari.data.asof import as_of
from prahari.data.financials import financial_table
from prahari.data.manual import read_manual
from prahari.data.market_cap import market_cap
from prahari.features.common import financial_snapshot


@dataclass
class FeatureSources:
    tables: dict[str, pd.DataFrame]
    panel_ids: tuple[str, ...]

    def snapshot(self, config: Config, t: str | pd.Timestamp, arena: str) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
        instant = pd.to_datetime(t, utc=True)
        tables = {name: as_of(table, instant) for name, table in self.tables.items()}
        settings = config.section("india_config")["market"]
        features = config.section("feature_config")
        market = tables["market"].copy()
        market["venue_priority"] = market.exchange.map({name: index for index, name in enumerate(settings["exchange_preference"])})
        market["series_priority"] = market.series.map({name: index for index, name in enumerate(settings["series"])})
        latest = market.sort_values(["period_end", "venue_priority", "series_priority"], ascending=[True, False, False]).drop_duplicates("entity_id", keep="last")
        traded = latest.loc[latest.period_end.ge(instant - pd.Timedelta(days=features["chs"]["maximum_quote_age_days"]))]
        if arena not in ("P", "U"):
            raise ValueError("Unknown arena")
        ids = set(self.panel_ids) | (set(traded.entity_id) if arena == "U" else set())
        result = pd.DataFrame({"entity_id": sorted(ids)})
        result["arena"], result["universe_mode"] = arena, "matched_panel" if arena == "P" else "market_only_fallback"
        # Cohort identifiers are evaluation sampling metadata, not outcomes or
        # historical score inputs. No event dates or role labels enter here.
        def merge(frame: pd.DataFrame, prefix: str) -> None:
            nonlocal result
            renamed = frame.rename(columns={"max_source_date": prefix + "_source_date", "is_synthetic": prefix + "_synthetic"})
            result = result.merge(renamed, on="entity_id", how="left", validate="one_to_one")
        merge(financial_snapshot(tables["financials"], features["financial_basis"]), "financial")
        meta = tables["entities"].sort_values(["period_end", "public_date"]).drop_duplicates("entity_id", keep="last")
        merge(meta[["entity_id", "name", "symbols", "sector", "is_financial", "max_source_date", "is_synthetic"]], "metadata")
        merge(traded[["entity_id", "symbol", "close", "max_source_date", "is_synthetic"]].rename(columns={"symbol": "quote_symbol"}), "price")
        result["symbols"] = result.symbols.combine_first(result.quote_symbol)
        caps = market_cap(tables["market"], tables["shares"], settings)
        merge(caps[["entity_id", "market_cap", "market_cap_reason", "max_source_date", "is_synthetic"]], "capital")
        result.loc[result.close.isna(), "market_cap"] = np.nan
        result.loc[result.close.isna(), "market_cap_reason"] = "missing_recent_public_quote"
        universe_caps = caps.loc[caps.entity_id.isin(traded.entity_id)]
        complete = not traded.empty and len(universe_caps) == len(traded) and universe_caps.market_cap.notna().all()
        result["universe_market_cap"] = universe_caps.market_cap.sum() if complete else np.nan
        result["universe_cap_source_date"] = universe_caps.max_source_date.max() if complete else pd.NaT
        result["universe_cap_synthetic"] = int(complete and universe_caps.is_synthetic.eq(1).any())
        fx = tables["fx"].loc[tables["fx"].entity_id.eq("USDINR")].sort_values(["period_end", "public_date"])
        fresh_fx = fx.loc[fx.period_end.ge(instant - pd.Timedelta(days=features["chs"]["maximum_fx_age_days"]))]
        result["inr_per_usd"] = fresh_fx.iloc[-1].inr_per_usd if not fresh_fx.empty else np.nan
        result["fx_source_date"] = fresh_fx.iloc[-1].max_source_date if not fresh_fx.empty else pd.NaT
        result["fx_synthetic"] = int(not fresh_fx.empty and fresh_fx.iloc[-1].is_synthetic == 1)
        result["financial_period_end"] = pd.to_datetime(result.financial_period_end, utc=True)
        con = tables["financials"].loc[tables["financials"].basis.eq("consolidated") & tables["financials"].field.eq("total_debt")]
        con = con[["entity_id", "period_end", "value", "max_source_date", "is_synthetic"]].rename(columns={
            "period_end": "financial_period_end", "value": "consolidated_total_debt", "max_source_date": "consolidated_source_date", "is_synthetic": "consolidated_synthetic"})
        result = result.merge(con, on=["entity_id", "financial_period_end"], how="left", validate="one_to_one")
        n = tables["nbfc"].sort_values(["period_end", "public_date"])
        fields = config.section("manual_config")["tables"]["nbfc_metrics"]["numeric"]
        current = n.drop_duplicates("entity_id", keep="last")[["entity_id", "period_end", "max_source_date", "is_synthetic", *fields]].rename(columns={"period_end": "nbfc_period_end"})
        merge(current, "nbfc")
        prior_dates, prior_taints = [], []
        for name in ("gnpa_pct", "nim_pct"):
            values = []
            for row in result.itertuples():
                past = n.loc[n.entity_id.eq(row.entity_id) & n.period_end.eq(row.nbfc_period_end - pd.DateOffset(years=1))] if pd.notna(row.nbfc_period_end) else n.iloc[:0]
                values.append(past.iloc[-1][name] if not past.empty else np.nan)
                if name == "gnpa_pct":
                    prior_dates.append(past.max_source_date.max() if not past.empty else pd.NaT)
                    prior_taints.append(int(not past.empty and past.is_synthetic.eq(1).any()))
            result[name + "_prev1"] = values
        result["nbfc_prior_source_date"], result["nbfc_prior_synthetic"] = prior_dates, prior_taints
        result["peer_loan_growth_median"] = np.nan
        for _, group in result.loc[result.is_financial.eq(1)].groupby("sector"):
            for index in group.index:
                other = group.drop(index).loan_book_growth.dropna()
                if len(other) >= features["nbfc"]["minimum_cross_section"]:
                    result.loc[index, "peer_loan_growth_median"] = other.median()
        dates = [name for name in result if name.endswith("_source_date")]
        for name in dates:
            result[name] = pd.to_datetime(result[name], utc=True)
        result["max_source_date"] = result[dates].max(axis=1)
        result["is_synthetic"] = result[[name for name in result if name.endswith("_synthetic")]].eq(1).any(axis=1).astype(int)
        result["needs_verification"] = result.max_source_date.isna().astype(int)
        result.attrs["as_of"] = instant.isoformat()
        return result, tables


def load_feature_sources(config: Config) -> FeatureSources:
    """Never enumerate sealed folders; only configured public tables are loaded."""
    files = sorted([*config.path("market_cache").glob("bhavcopy_*.parquet"), *config.path("market_cache").glob("bse_*.parquet")])
    if not files:
        raise FileNotFoundError("No public market cache")
    markets = []
    for path in files:
        table = pd.read_parquet(path)
        if "exchange" not in table:
            table["exchange"] = "bse" if path.name.startswith("bse_") else "nse"
        markets.append(table)
    index_files = sorted(config.path("market_cache").glob("index_*.parquet"))
    indices = pd.concat([pd.read_parquet(path) for path in index_files], ignore_index=True) if index_files else pd.DataFrame(columns=[
        "entity_id", "period_end", "public_date", "date_is_imputed", "needs_verification", "is_synthetic", "source_url", "close"])
    shares = read_manual(config, "share_counts")
    shares["field"], shares["value"] = "shares_outstanding", shares.shares_outstanding
    events, peers = read_manual(config, "events"), read_manual(config, "peers")
    ids = tuple(sorted(set(events.loc[events.needs_verification.eq(0), "entity_id"]) | set(peers.loc[peers.needs_verification.eq(0), "entity_id"])))
    tables = {"financials": financial_table(config), "market": pd.concat(markets, ignore_index=True),
              "indices": indices, "entities": read_manual(config, "entities"), "shares": shares,
              "pledges": read_manual(config, "shareholding"), "ratings": read_manual(config, "rating_actions"),
              "governance": read_manual(config, "governance_events"), "nbfc": read_manual(config, "nbfc_metrics")}
    tables["fx"] = read_manual(config, "fx_rates")
    tables["signal_coverage"] = read_manual(config, "signal_coverage")
    return FeatureSources(tables, ids)
