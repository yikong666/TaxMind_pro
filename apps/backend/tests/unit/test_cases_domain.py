from __future__ import annotations

import pytest

from taxmind.modules.cases.domain import (
    reject_restricted_identifiers,
    validate_synthetic_or_anonymized,
)
from taxmind.shared.domain.errors import DomainError


def test_cases_only_accept_synthetic_or_anonymized_data() -> None:
    assert validate_synthetic_or_anonymized("SYNTHETIC") == "synthetic"
    assert validate_synthetic_or_anonymized("anonymized") == "anonymized"

    with pytest.raises(DomainError) as error:
        validate_synthetic_or_anonymized("real_customer")

    assert error.value.code == "VALIDATION_FAILED"


def test_cases_reject_common_restricted_identifiers_recursively() -> None:
    with pytest.raises(DomainError) as error:
        reject_restricted_identifiers({"customer": ["联系电话13800138000"]})

    assert error.value.code == "SENSITIVE_DATA_NOT_ALLOWED"
