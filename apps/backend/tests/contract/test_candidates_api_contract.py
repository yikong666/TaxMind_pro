from __future__ import annotations

from pathlib import Path

from taxmind.bootstrap.settings import Settings
from taxmind.entrypoints.api.main import create_app


def test_openapi_exposes_review_gated_candidate_batch_and_queue(tmp_path: Path) -> None:
    schema = create_app(
        Settings(app_env="test", app_debug=False, log_dir=tmp_path / "logs")
    ).openapi()

    batch_path = schema["paths"][
        "/api/v1/knowledge/document-versions/{version_id}/candidate-batches"
    ]["post"]
    assert batch_path["responses"]["201"]["description"]
    response_ref = batch_path["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
    response_name = response_ref.rsplit("/", maxsplit=1)[-1]
    data_ref = schema["components"]["schemas"][response_name]["properties"]["data"]["$ref"]
    data_name = data_ref.rsplit("/", maxsplit=1)[-1]
    batch_properties = schema["components"]["schemas"][data_name]["properties"]["batch"]
    assert batch_properties["$ref"].endswith("CandidateBatchData")

    queue_path = schema["paths"]["/api/v1/knowledge/candidates"]["get"]
    assert queue_path["responses"]["200"]["description"]
    assert {parameter["name"] for parameter in queue_path["parameters"]} == {"limit"}

    approved_queue_path = schema["paths"]["/api/v1/knowledge/candidates/approved"]["get"]
    assert approved_queue_path["responses"]["200"]["description"]
    assert {parameter["name"] for parameter in approved_queue_path["parameters"]} == {"limit"}

    review_path = schema["paths"]["/api/v1/knowledge/candidates/{candidate_id}/review"]["post"]
    review_schema = review_path["requestBody"]["content"]["application/json"]["schema"]
    review_name = review_schema["$ref"].rsplit("/", maxsplit=1)[-1]
    assert schema["components"]["schemas"][review_name]["properties"]["decision"]["pattern"] == (
        "^(approved|rejected)$"
    )

    publish_path = schema["paths"]["/api/v1/knowledge/publish-batches"]["post"]
    assert publish_path["responses"]["201"]["description"]
    publish_queue_path = schema["paths"]["/api/v1/knowledge/publish-batches"]["get"]
    assert publish_queue_path["responses"]["200"]["description"]
    assert {parameter["name"] for parameter in publish_queue_path["parameters"]} == {"limit"}
    validate_path = schema["paths"]["/api/v1/knowledge/publish-batches/{batch_id}/validate"]["post"]
    assert validate_path["responses"]["200"]["description"]

    snapshot_path = schema["paths"][
        "/api/v1/knowledge/publish-batches/{batch_id}/materialize-snapshot"
    ]["post"]
    assert snapshot_path["responses"]["201"]["description"]
    snapshot_response_ref = snapshot_path["responses"]["201"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    snapshot_response_name = snapshot_response_ref.rsplit("/", maxsplit=1)[-1]
    snapshot_data_ref = schema["components"]["schemas"][snapshot_response_name]["properties"][
        "data"
    ]["$ref"]
    snapshot_data_name = snapshot_data_ref.rsplit("/", maxsplit=1)[-1]
    snapshot_properties = schema["components"]["schemas"][snapshot_data_name]["properties"]
    assert snapshot_properties["status"]["type"] == "string"
    assert snapshot_properties["pending_projection_event_count"]["type"] == "integer"
