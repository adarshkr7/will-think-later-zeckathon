from pathlib import Path

import pandas as pd
import pytest

from prahari.data.asof import as_of
from prahari.data.events import qualifying_event_evidence, validate_event_evidence
from prahari.eval.panel_quality import panel_acceptance


@pytest.fixture
def evidence():
    return pd.read_csv(Path(__file__).parent / "fixtures" / "event_evidence.csv")


def test_cured_d_rule_applies_to_every_company(config, evidence):
    known = qualifying_event_evidence(evidence, config.section("india_config")["events"])
    ratings = known.loc[known.event_type.eq("D_rating")].set_index("entity_id")
    assert ratings.period_end.to_dict() == {"FIX_A": "2019-01-03", "FIX_B": "2021-01-01"}


def test_unknown_cure_status_cannot_count_as_uncured(config, evidence):
    evidence.loc[evidence.event_type.eq("D_rating"), "cured_before_final_default"] = float("nan")
    with pytest.raises(ValueError, match="cure determination"):
        qualifying_event_evidence(evidence, config.section("india_config")["events"])


def test_later_components_retain_their_own_publication_dates(evidence):
    snapshot = as_of(evidence, "2019-01-04")
    assert not snapshot.event_type.eq("cirp").any()
    assert not as_of(evidence, "2019-01-03").period_end.eq(pd.Timestamp("2019-01-01", tz="UTC")).any()


def test_event_date_and_publication_must_match_component_evidence(config, evidence):
    # This is an in-memory synthetic outcome, never written to production.
    events = pd.DataFrame([{
        "entity_id": "FIX_A", "first_payment_default_date": "2019-01-01",
        "first_D_rating_date": "2019-01-03", "cirp_admission_date": "2020-01-01",
        "event_date": "2019-01-01", "public_date": "2019-01-03", "source_urls": "fixture://a-payment",
        "needs_verification": 0, "is_synthetic": 1,
    }])
    settings = config.section("india_config")["events"]
    validate_event_evidence(events, evidence, settings)
    events.loc[0, "public_date"] = "2019-01-01"
    with pytest.raises(ValueError, match="first source publication"):
        validate_event_evidence(events, evidence, settings)
    events.loc[0, "public_date"] = "2019-01-03"
    events.loc[0, "first_D_rating_date"] = "2010-01-01"
    with pytest.raises(ValueError, match="qualifying evidence"):
        validate_event_evidence(events, evidence, settings)


def test_verified_dates_do_not_pass_missing_classification_gate(config, evidence):
    events = evidence.loc[evidence.entity_id.eq("FIX_A")].head(1).assign(
        sector=None, is_financial=None, nse_symbol=None, bse_code=None, isin=None)
    peers = pd.DataFrame(columns=["entity_id", "needs_verification", "matched_to", "is_stressed_survivor", "is_synthetic"])
    checks = panel_acceptance(events, peers, pd.DataFrame(), pd.DataFrame(), config.section("india_config")["panel"])
    assert checks.set_index("check").loc["case_identity_and_classification", "passed"] == 0
