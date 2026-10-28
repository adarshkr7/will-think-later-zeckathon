"""Classical screens. Missing inputs remain unknown, including binary screens."""

from __future__ import annotations

from typing import Mapping

import pandas as pd

from prahari.features.common import Value, divide, evaluate, feature_frame, number


def _z_inputs(v: Mapping, market: bool) -> dict[str, float]:
    n = lambda key: number(v, key)
    ta, tl = n("total_assets"), n("total_liabilities")
    return {"wc_ta": divide(n("current_assets") - n("current_liabilities"), ta),
            "re_ta": divide(n("retained_earnings"), ta), "ebit_ta": divide(n("ebit"), ta),
            ("me_tl" if market else "equity_tl"): divide(n("market_cap" if market else "equity"), tl),
            **({"sales_ta": divide(n("revenue"), ta)} if market else {})}


def altman_classic(v: Mapping, coefficients: Mapping) -> Value:
    """Altman (1968), JF 23:589–609, doi:10.1111/j.1540-6261.1968.tb00843.x.

    Raw-ratio form with market equity / book total liabilities. No EBITDA proxy.
    """
    return evaluate(lambda: sum(coefficients[key] * value for key, value in _z_inputs(v, True).items()))


def altman_em(v: Mapping, coefficients: Mapping) -> Value:
    """Altman, Hartzell & Peck (1995), Emerging Market Corporate Bonds; plan Z'' EM.

    The specified EM variant includes the 3.25 intercept and book equity/TL.
    """
    return evaluate(lambda: coefficients["intercept"] + sum(coefficients[key] * value for key, value in _z_inputs(v, False).items()))


def hillegeist(v: Mapping, settings: Mapping) -> Value:
    """Hillegeist et al. (2004), RAST 9:5–34, updated Z logit, Table 2.

    Coefficients verified against authors' bankruptcy12.pdf, p.39. This is a
    US-estimated logit screen, not a calibrated Indian default probability.
    """
    return evaluate(lambda: settings["intercept"] + sum(settings["weights"][key] * value for key, value in _z_inputs(v, True).items()))


def beneish_indices(v: Mapping) -> dict[str, Value]:
    """Beneish (1999), FAJ 55(5):24–36, doi:10.2469/faj.v55.n5.2296.

    TATA uses explicitly sourced income from continuing operations and CFO.
    LVGI uses long-term debt plus current liabilities, not all liabilities.
    """
    n = lambda key, lag=False: number(v, key + ("_prev1" if lag else ""))
    d = divide
    calculations = {
        "dsri": lambda: d(d(n("receivables"), n("revenue")), d(n("receivables", True), n("revenue", True))),
        "gmi": lambda: d(d(n("revenue", True) - n("cogs", True), n("revenue", True)), d(n("revenue") - n("cogs"), n("revenue"))),
        "aqi": lambda: d(1 - d(n("current_assets") + n("ppe_net"), n("total_assets")), 1 - d(n("current_assets", True) + n("ppe_net", True), n("total_assets", True))),
        "sgi": lambda: d(n("revenue"), n("revenue", True)),
        "depi": lambda: d(d(n("depreciation", True), n("ppe_net", True) + n("depreciation", True)), d(n("depreciation"), n("ppe_net") + n("depreciation"))),
        "sgai": lambda: d(d(n("sga"), n("revenue")), d(n("sga", True), n("revenue", True))),
        "tata": lambda: d(n("income_continuing") - n("cfo"), n("total_assets")),
        "lvgi": lambda: d(d(n("lt_debt") + n("current_liabilities"), n("total_assets")), d(n("lt_debt", True) + n("current_liabilities", True), n("total_assets", True))),
    }
    return {key: evaluate(function) for key, function in calculations.items()}


def beneish(v: Mapping, settings: Mapping) -> Value:
    """Beneish (1999) eight-variable unweighted probit index; not an Indian PD."""
    indices = beneish_indices(v)
    failed = [f"{key}:{result.reason}" for key, result in indices.items() if result.reason]
    if failed:
        return Value(float("nan"), ";".join(failed))
    return Value(settings["intercept"] + sum(settings["weights"][key] * result.value for key, result in indices.items()))


def piotroski(v: Mapping) -> Value:
    """Piotroski (2000), JAR 38:1–41, nine signals; author reprint pp.9–10,15.

    ROA/CFO use beginning assets. Leverage and turnover use average assets
    (Table 1). Debt includes current maturities. Equity issuance is explicit;
    a change in raw share count is not assumed to be an issuance.
    """
    def calculate() -> float:
        n = lambda key, lag=0: number(v, key + (f"_prev{lag}" if lag else ""))
        ta, prev, prev2 = n("total_assets"), n("total_assets", 1), n("total_assets", 2)
        roa, roa_prev = divide(n("income_before_extraordinary"), prev), divide(n("income_before_extraordinary", 1), prev2)
        cfo = divide(n("cfo"), prev)
        leverage = lambda lag, avg: divide(n("lt_debt", lag) + n("current_maturities_lt_debt", lag), avg)
        margin = lambda lag: divide(n("revenue", lag) - n("cogs", lag), n("revenue", lag))
        issuance = n("equity_issued")
        if issuance not in (0, 1):
            from prahari.features.common import MissingInput
            raise MissingInput("invalid:equity_issued")
        return sum([roa > 0, cfo > 0, roa > roa_prev, cfo > roa,
                    leverage(0, (ta + prev) / 2) < leverage(1, (prev + prev2) / 2),
                    divide(n("current_assets"), n("current_liabilities")) > divide(n("current_assets", 1), n("current_liabilities", 1)),
                    issuance == 0, margin(0) > margin(1),
                    divide(n("revenue"), (ta + prev) / 2) > divide(n("revenue", 1), (prev + prev2) / 2)])
    return evaluate(calculate)


def forensic_features(table: pd.DataFrame, settings: dict) -> pd.DataFrame:
    functions = {"z_classic": lambda v: altman_classic(v, settings["altman"]["classic"]),
                 "z_em": lambda v: altman_em(v, settings["altman"]["em"]),
                 "hillegeist_logit": lambda v: hillegeist(v, settings["hillegeist"]),
                 "m_score": lambda v: beneish(v, settings["beneish"]), "f_score": piotroski}
    functions.update({key: (lambda v, key=key: beneish_indices(v)[key]) for key in settings["beneish"]["weights"]})
    return feature_frame(table, functions, financial_exempt=True)
