import pytest

from prahari.data.entity_review import require_reviewed_text


def test_classification_review_checks_literal_source_proof():
    require_reviewed_text("An infra-structure financing NBFC.", ["infrastructure financing", "NBFC"])
    with pytest.raises(ValueError, match="changed or is missing"):
        require_reviewed_text("A textile manufacturer.", ["housing finance"])
    with pytest.raises(ValueError, match="changed or is missing"):
        require_reviewed_text("Anything", [])
