"""Campbell–Hilscher–Szilagyi market features and published failure logit."""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

from prahari.features.common import Value, divide, evaluate, number, require_snapshot


def weighted_average(values: list[float], decay: float) -> Value:
    """CHS (2008), JF 63:2899–2939: normalized geometric weights, newest first."""
    def calculate() -> float:
        array = np.asarray(values, dtype=float)
        if not len(array) or not np.isfinite(array).all() or not 0 < decay < 1:
            from prahari.features.common import MissingInput
            raise MissingInput("incomplete_weighted_history")
        weights = decay ** np.arange(len(array))
        return float(np.dot(array, weights) / weights.sum())
    return evaluate(calculate)


def chs_accounting(v: Mapping, settings: dict) -> dict[str, Value]:
    """CHS market-valued assets TL+ME; annual NI/4 adaptation per plan §3.3.

    MB here follows the plan's ME/book-equity variant. US price units and
    negative-book floor require explicit configured values; neither is guessed.
    """
    n = lambda key: number(v, key)
    mta = lambda: n("total_liabilities") + n("market_cap")
    return {"nimta": evaluate(lambda: divide(n("pat") / settings["annual_ni_divisor"], mta(), "market_total_assets")),
            "tlmta": evaluate(lambda: divide(n("total_liabilities"), mta(), "market_total_assets")),
            "cashmta": evaluate(lambda: divide(n("cash_and_st_investments"), mta(), "market_total_assets")),
            "relsize": evaluate(lambda: np.log(divide(n("market_cap"), n("universe_market_cap"), "universe_market_cap"))),
            "mb": evaluate(lambda: divide(n("market_cap"), max(n("equity"), number(settings, "book_equity_floor_inr")), "book_equity_floor")),
            "price": evaluate(lambda: np.log(min(divide(n("close"), n("inr_per_usd"), "inr_per_usd"), number(settings, "price_cap_usd"))))}


def chs_score(values: Mapping, settings: Mapping) -> Value:
    """CHS (2008), Table IV twelve-month coefficients; not a calibrated Indian PD.

    Coefficients remain in config. Published score is distinguished from its
    Indian plan adaptations (annual NI proxy, universe-relative size and MB).
    """
    return evaluate(lambda: settings["intercept"] + sum(weight * number(values, name) for name, weight in settings["weights"].items()))


def relative_chs_features(table: pd.DataFrame, settings: Mapping) -> pd.DataFrame:
    """Exactly identify median/IQR-standardized CHS without inventing universe ME.

    CHS (2008), Table IV, is linear in RSIZE=log(ME_i)-log(ME_universe).
    Replacing RSIZE with log(ME_i)-median(log(ME)) adds one common constant
    to every otherwise eligible score. Subtracting the cross-section median
    removes that constant, and IQR is translation invariant. This is an
    algebraic identity, not a missing-value zero or an estimated market total.
    Raw RSIZE and raw CHS remain unknown when their denominator is unknown.
    """
    require_snapshot(table)
    weights = settings["weights"]
    other_names = [name for name in weights if name != "relsize"]
    other = table.reindex(columns=other_names).apply(pd.to_numeric, errors="raise").replace([np.inf, -np.inf], np.nan)
    capital = pd.to_numeric(table.market_cap, errors="raise").replace([np.inf, -np.inf], np.nan)
    logs = np.log(capital.where(capital.gt(0)))
    eligible = other.notna().all(axis=1) & logs.notna()
    center = logs.loc[eligible].median() if eligible.any() else np.nan
    result = table[["entity_id", "max_source_date", "is_synthetic"]].copy()
    result["market_size_centered"] = (logs-center).where(eligible)
    result["market_size_centered__reason"] = np.where(eligible, "", "incomplete_chs_inputs_or_market_equity")
    projection = (settings["intercept"] + other.mul(pd.Series({name: weights[name] for name in other_names})).sum(axis=1, min_count=len(other_names))
                  + weights["relsize"]*result.market_size_centered).where(eligible)
    result["chs_relative_score"] = projection
    result["chs_relative_score__reason"] = np.where(eligible, "", "incomplete_chs_inputs_or_market_equity")
    result["chs_center"], result["chs_scale"], result["chs_standardized"] = np.nan, np.nan, np.nan
    result["chs_standardized__reason"] = "insufficient_cross_section_spread"
    known = projection.dropna()
    if len(known) > 1:
        spread = known.quantile(.75)-known.quantile(.25)
        if spread > 0:
            result["chs_center"], result["chs_scale"] = known.median(), spread
            result["chs_standardized"] = (projection-known.median())/spread
            result.loc[eligible, "chs_standardized__reason"] = ""
    result["chs_standardization_basis"] = "centered_market_size"
    if eligible.any():
        result.loc[eligible, "max_source_date"] = table.max_source_date.max()
        if table.is_synthetic.eq(1).any():
            result.loc[eligible, "is_synthetic"] = 1
    result.attrs.update(table.attrs)
    return result


def market_statistics(prices: pd.DataFrame, indices: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Past-only raw-price log excess returns and annualized daily volatility.

    No missing month is assigned a zero return. Raw bhavcopy prices are not
    silently claimed corporate-action-adjusted; the basis is carried explicitly.
    """
    require_snapshot(prices)
    require_snapshot(indices)
    cutoff = pd.to_datetime(prices.attrs["as_of"], utc=True)
    if prices.attrs["as_of"] != indices.attrs["as_of"]:
        raise ValueError("Return and index cutoffs differ")
    rows = []
    for entity, group in prices.groupby("entity_id", sort=True):
        group = group.copy()
        group["venue_priority"] = group.exchange.ne(settings["preferred_exchange"]).astype(int)
        daily = group.sort_values(["period_end", "venue_priority"]).drop_duplicates("period_end", keep="first")
        recent = daily.loc[daily.period_end.ge(cutoff - pd.DateOffset(months=settings["volatility_months"]))]
        returns = recent.close.pct_change(fill_method=None).dropna()
        sigma = Value(float(returns.std(ddof=1) * np.sqrt(settings["annual_trading_days"]))) if len(returns) >= settings["minimum_daily_returns"] else Value(np.nan, "insufficient_daily_returns")
        excess = Value(np.nan, "incomplete_monthly_index_or_prices")
        window = daily.loc[daily.period_end.ge(cutoff - pd.DateOffset(months=settings["drawdown_months"]))]
        drawdown = Value(np.nan, "incomplete_52_week_price_window")
        if len(window) >= settings["minimum_drawdown_observations"] and window.close.gt(0).all():
            if window.period_end.max() >= cutoff - pd.Timedelta(days=settings["maximum_quote_age_days"]):
                drawdown = evaluate(lambda: divide(window.iloc[-1].close, window.close.max(), "52_week_high") - 1)
        # Only complete past calendar months; no current-month partial return.
        months = pd.period_range(end=(cutoff.tz_localize(None).to_period("M") - 1), periods=settings["return_months"] + 1, freq="M")
        for index_id in settings["index_ids"]:
            benchmark = indices.loc[indices.entity_id.eq(index_id)]
            if benchmark.empty:
                continue
            def monthly(table: pd.DataFrame) -> pd.Series:
                last = table.sort_values("period_end").copy()
                last["month"] = last.period_end.dt.tz_localize(None).dt.to_period("M")
                last = last.drop_duplicates("month", keep="last").set_index("month").reindex(months)
                # A quote far from month-end is a missing monthly observation.
                ends = pd.Series(months.to_timestamp(how="end").normalize().tz_localize("UTC"), index=months)
                stale = (ends - last.period_end).dt.days.gt(settings["maximum_quote_age_days"])
                return last.close.where(~stale)
            stock, index = monthly(daily), monthly(benchmark)
            if stock.notna().all() and index.notna().all() and stock.gt(0).all() and index.gt(0).all():
                log_excess = np.log(stock / stock.shift(1)) - np.log(index / index.shift(1))
                excess = weighted_average(log_excess.dropna().iloc[::-1].tolist(), settings["monthly_decay"])
                break
        source_date = max(group.max_source_date.max(), indices.max_source_date.max()) if not indices.empty else group.max_source_date.max()
        rows.append({"entity_id": entity, "sigma": sigma.value, "sigma__reason": sigma.reason,
                     "drawdown_52w": drawdown.value, "drawdown_52w__reason": drawdown.reason,
                     "exretavg": excess.value, "exretavg__reason": excess.reason,
                     "market_return_basis": "unadjusted_price_returns", "max_source_date": source_date,
                     "is_synthetic": int(group.is_synthetic.eq(1).any() or indices.is_synthetic.eq(1).any())})
    result = pd.DataFrame(rows, columns=["entity_id", "sigma", "sigma__reason", "drawdown_52w", "drawdown_52w__reason", "exretavg", "exretavg__reason", "market_return_basis", "max_source_date", "is_synthetic"])
    result.attrs.update(prices.attrs)
    return result
