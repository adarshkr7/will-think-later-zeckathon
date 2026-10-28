import pandas as pd

from prahari.eval.panel_quality import audit_financial_histories


def test_old_financial_years_do_not_satisfy_pre_event_coverage(config, monkeypatch):
    case = pd.DataFrame([{"entity_id": "FIX_CASE", "event_date": "2020-01-01", "is_financial": 0,
                          "needs_verification": 0, "is_synthetic": 1}])
    peers = pd.DataFrame(columns=["entity_id", "matched_to", "needs_verification", "is_financial", "is_synthetic"])
    required = config.section("india_config")["financials"]["required_nonfinancial"]
    rows = [{"entity_id": "FIX_CASE", "field": field, "value": 1, "basis": "standalone",
             "period_end": f"{year}-03-31", "public_date": "2011-09-30", "source_doc": "fixture://history",
             "date_is_imputed": 0, "needs_verification": 0, "is_synthetic": 1}
            for year in (2008, 2009, 2010) for field in required]
    monkeypatch.setattr("prahari.eval.panel_quality.read_manual", lambda c, name: case if name == "events" else peers)
    monkeypatch.setattr("prahari.eval.panel_quality.financial_table", lambda c: pd.DataFrame(rows))
    result = audit_financial_histories(config)
    assert result.complete_years.item() == 0
    assert result.complete.item() == 0
    assert result.is_synthetic.item() == 1
