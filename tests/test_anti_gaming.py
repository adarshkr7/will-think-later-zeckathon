import pandas as pd
import pytest

from conftest import FIXTURES
from prahari.eval.anti_gaming import perturb_statement
from prahari.features.common import MissingInput


def test_interventions_preserve_baseline_cash_and_declared_accounting_identities(config):
    source = pd.read_csv(FIXTURES / "anti_gaming.csv").iloc[0].to_dict()
    settings = config.section("diagnostics_config")["anti_gaming"]
    accrual = {**source, **perturb_statement(source, "accrual_inflation", settings)}
    assert accrual["pat"] == 13 and accrual["cfo"] == source["cfo"]
    assert accrual["total_assets"] == accrual["total_liabilities"]+accrual["equity"]
    spv = {**source, **perturb_statement(source, "spv_debt_shift", settings)}
    assert spv["total_debt"] == 30 and spv["consolidated_total_debt"] == 70
    rollover = {**source, **perturb_statement(source, "cp_rollover", settings)}
    assert rollover["commercial_paper"] == 0
    assert rollover["st_borrowings"]+rollover["lt_debt"] == source["total_debt"]
    assert source["pat"] == 10 and source["commercial_paper"] == 5
    incomplete = {**source, "cfo": float("nan")}
    with pytest.raises(MissingInput):
        perturb_statement(incomplete, "accrual_inflation", settings)
