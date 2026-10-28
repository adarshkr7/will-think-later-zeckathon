import pandas as pd

from prahari.features.soft import rating_change, rating_symbol


def test_long_and_short_d_are_resolved_within_the_instrument_scale(config):
    settings = config.section("feature_config")["soft"]
    assert rating_symbol("CARE AA-", settings) == ("long", 4)
    assert rating_change("[ICRA]AAA", "[ICRA]D", settings) == 19
    assert rating_change("[ICRA]A4+", "[ICRA]D", settings) == 2
    assert pd.isna(rating_change("CARE AAA", "CARE A1+", settings))
    assert pd.isna(rating_change("withdrawn", "CARE D", settings))
