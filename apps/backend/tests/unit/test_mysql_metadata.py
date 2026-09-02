import taxmind.modules.audit.infrastructure.models as audit_models  # noqa: F401
import taxmind.modules.cases.infrastructure.models as cases_models  # noqa: F401
import taxmind.modules.conversations.infrastructure.models as conversation_models  # noqa: F401
import taxmind.modules.feedback.infrastructure.models as feedback_models  # noqa: F401
import taxmind.modules.identity.infrastructure.models as identity_models  # noqa: F401
import taxmind.modules.knowledge.infrastructure.models as knowledge_models  # noqa: F401
import taxmind.modules.sources.infrastructure.models as source_models  # noqa: F401
from taxmind.bootstrap.settings import Settings
from taxmind.infrastructure.mysql.base import Base
from taxmind.infrastructure.mysql.session import database_url


def test_database_url_hides_password_when_rendered_for_diagnostics() -> None:
    settings = Settings(mysql_password="test-secret")  # noqa: S106

    rendered = database_url(settings).render_as_string(hide_password=True)

    assert "test-secret" not in rendered
    assert "mysql+asyncmy" in rendered


def test_identity_and_audit_tables_are_registered_in_shared_metadata() -> None:
    assert {"organizations", "users", "organization_members", "audit_logs"} <= set(
        Base.metadata.tables
    )


def test_conversation_tables_are_registered_in_shared_metadata() -> None:
    assert {"conversations", "messages", "conversation_summaries"} <= set(Base.metadata.tables)


def test_feedback_tables_are_registered_in_shared_metadata() -> None:
    assert {"feedback_items"} <= set(Base.metadata.tables)


def test_offline_knowledge_governance_tables_are_registered_in_shared_metadata() -> None:
    expected = {
        "source_sites",
        "ingestion_jobs",
        "knowledge_candidate_batches",
        "knowledge_candidates",
        "knowledge_publish_batches",
        "knowledge_publish_batch_items",
        "knowledge_snapshots",
        "knowledge_snapshot_items",
        "outbox_events",
        "projection_sync_states",
    }

    assert expected <= set(Base.metadata.tables)
