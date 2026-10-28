import io
import zipfile

from conftest import FIXTURES
from prahari.data.bhavcopy import parse_bhavcopy


def test_symbol_only_archives_preserve_real_prices_without_guessing_isins(config):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("fixture.csv", (FIXTURES / "bhavcopy_symbol_only.csv").read_bytes())
    result = parse_bhavcopy(payload.getvalue(), "fixture://legacy", config.section("india_config")["market"])
    assert result.entity_id.item() == "NSE:FIX_LEGACY"
    assert result.close.item() == 10
    assert result.needs_verification.item() == 1
    assert result.is_synthetic.item() == 1
