from datetime import date

import pytest

from taxmind.modules.procedures.domain import ProcedureDefinition


def test_published_procedure_requires_official_source_and_valid_effective_period() -> None:
    procedure = ProcedureDefinition(
        procedure_version_id="procedure-v1",
        procedure_code="invoice-red-letter",
        title="红字发票开具",
        region_code="440300",
        effective_start=date(2026, 1, 1),
        effective_end=None,
        review_status="published",
        official_url="https://example.gov.cn/procedures/red-letter-invoice",
        source_chunk_ids=("chunk-1",),
        materials=("虚构材料清单",),
        channels=("线上办理",),
    )

    assert procedure.procedure_code == "invoice-red-letter"

    with pytest.raises(ValueError, match="official_url"):
        ProcedureDefinition(
            procedure_version_id="procedure-v2",
            procedure_code="missing-source",
            title="虚构事项",
            region_code="440300",
            effective_start=date(2026, 1, 1),
            effective_end=None,
            review_status="published",
            official_url="",
            source_chunk_ids=("chunk-1",),
            materials=(),
            channels=(),
        )

    with pytest.raises(ValueError, match="effective_end"):
        ProcedureDefinition(
            procedure_version_id="procedure-v3",
            procedure_code="invalid-period",
            title="虚构事项",
            region_code="440300",
            effective_start=date(2026, 2, 1),
            effective_end=date(2026, 1, 1),
            review_status="published",
            official_url="https://example.gov.cn/procedures/invalid-period",
            source_chunk_ids=("chunk-1",),
            materials=(),
            channels=(),
        )
