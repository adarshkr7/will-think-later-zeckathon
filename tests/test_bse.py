import io
import zipfile
import pytest

from prahari.data.bse import parse_bse
from conftest import FIXTURES


def test_bse_does_not_guess_isins_from_names(config):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("EQ280918.CSV", (FIXTURES / "bse.csv").read_bytes())
    result = parse_bse(payload.getvalue(), "fixture://bse", "2018-09-28", config.section("india_config")["market"])
    assert list(result.entity_id) == ["BSE:FIX001", "BSE:FIX002"]
    assert result.needs_verification.eq(1).all()
    assert result.identity_reason.eq("unmapped_exchange_code").all()
    assert result.is_synthetic.eq(1).all()


def test_wrong_session_bse_archive_is_rejected(config):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("EQ280918.CSV", (FIXTURES / "bse.csv").read_bytes())
    with pytest.raises(ValueError, match="requested date"):
        parse_bse(payload.getvalue(), "fixture://bse", "2018-09-27", config.section("india_config")["market"])
