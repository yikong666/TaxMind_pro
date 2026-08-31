from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from taxmind.shared.domain.errors import DomainError


def _repository_relative_path(value: Path) -> Path:
    if value.is_absolute():
        return value
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "AGENTS.md").is_file():
            return candidate / value
    return current / value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "TaxMind Pro"
    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = True
    api_host: str = "0.0.0.0"  # noqa: S104 - container-friendly bind address
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_prefix: str = "/api/v1"
    web_origin: str = "http://localhost:5173"
    log_level: str = "INFO"
    log_json: bool = False
    log_dir: Path = Path("var/log/taxmind")
    build_sha: str = "development"
    contract_version: str = "v1"

    jwt_secret: SecretStr = SecretStr("replace-with-at-least-32-random-bytes")
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "taxmind-pro"
    access_token_ttl_minutes: int = Field(default=30, ge=1)
    refresh_token_ttl_days: int = Field(default=14, ge=1)
    stream_replay_ttl_seconds: int = Field(default=86400, ge=60)

    mysql_image: str = "mysql:8.4"
    mysql_host: str = "127.0.0.1"
    mysql_port: int = Field(default=3306, ge=1, le=65535)
    mysql_database: str = "taxmind"
    mysql_user: str = "taxmind"
    mysql_password: SecretStr = SecretStr("taxmind-dev-only")
    mysql_root_password: SecretStr = SecretStr("root-dev-only")
    mysql_pool_size: int = Field(default=10, ge=1)
    mysql_max_overflow: int = Field(default=20, ge=0)

    redis_image: str = "redis:7.4-alpine"
    redis_url: str = "redis://127.0.0.1:6379/0"
    celery_broker_url: str = "redis://127.0.0.1:6379/1"
    celery_result_backend: str = "redis://127.0.0.1:6379/2"
    short_memory_ttl_seconds: int = Field(default=259200, ge=60)
    short_memory_recent_message_limit: int = Field(default=20, ge=1, le=50)
    public_cache_ttl_seconds: int = Field(default=600, ge=1)

    minio_endpoint: str = "127.0.0.1:9000"
    minio_access_key: SecretStr = SecretStr("taxmind-minio")
    minio_secret_key: SecretStr = SecretStr("taxmind-minio-dev-only")
    minio_secure: bool = False
    minio_raw_bucket: str = "taxmind-raw"
    minio_parsed_bucket: str = "taxmind-parsed"
    minio_exports_bucket: str = "taxmind-exports"
    minio_temp_bucket: str = "taxmind-temp"

    milvus_uri: str = "http://127.0.0.1:19530"
    milvus_token: SecretStr = SecretStr("")
    milvus_database: str = "taxmind"
    milvus_policy_alias: str = "policy_chunks_current"
    milvus_faq_alias: str = "faq_questions_current"
    milvus_case_alias: str = "approved_case_memories_current"
    embedding_dimension: int = Field(default=1024, ge=1)

    neo4j_uri: str = "bolt://127.0.0.1:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("taxmind-neo4j-dev-only")
    neo4j_database: str = "neo4j"
    neo4j_query_timeout_seconds: int = Field(default=5, ge=1)
    neo4j_max_path_depth: int = Field(default=4, ge=1, le=4)

    # The key is supplied only through DASHSCOPE_API_KEY.  It must never be
    # serialised into API responses, logs, source files, or audit payloads.
    dashscope_api_key: SecretStr = SecretStr("replace-me")
    dashscope_llm_model: Literal["qwen-max", "qwen3-max"] = "qwen-max"
    dashscope_temperature: float = Field(default=0.1, ge=0, le=2)
    llm_timeout_seconds: int = Field(default=45, ge=1)
    llm_max_retries: int = Field(default=2, ge=0, le=2)
    embedding_provider: str = "fake"
    embedding_model: str = "BAAI/bge-m3"
    embedding_model_version: str = "initial"
    reranker_provider: str = "fake"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_model_version: str = "initial"
    model_device: str = "auto"

    dense_top_k: int = Field(default=30, ge=1, le=100)
    sparse_top_k: int = Field(default=30, ge=1, le=100)
    faq_top_k: int = Field(default=10, ge=1, le=100)
    rerank_candidate_limit: int = Field(default=40, ge=1, le=100)
    evidence_limit: int = Field(default=12, ge=1, le=20)
    rrf_k: int = Field(default=60, ge=1)

    ingestion_user_agent: str = "TaxMindProKnowledgeBot/0.1 contact=replace-me"
    ingestion_max_bytes: int = Field(default=52428800, ge=1)
    ingestion_requests_per_minute_per_domain: int = Field(default=6, ge=1)
    ingestion_connect_timeout_seconds: int = Field(default=5, ge=1)
    ingestion_read_timeout_seconds: int = Field(default=20, ge=1)

    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    metrics_enabled: bool = True

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("unsupported log level")
        return normalized

    @field_validator("log_dir")
    @classmethod
    def resolve_log_dir(cls, value: Path) -> Path:
        return _repository_relative_path(value)


def get_settings() -> Settings:
    return Settings()


def validate_runtime_settings(settings: Settings) -> None:
    """Validate unsafe combinations without contacting external services."""
    if settings.app_env != "production":
        return
    secret = settings.jwt_secret.get_secret_value()
    if len(secret) < 32 or secret.startswith("replace-"):
        raise DomainError(
            code="CONFIGURATION_INVALID",
            message="生产环境 JWT_SECRET 必须使用至少 32 字节的随机值",
        )
    if settings.app_debug:
        raise DomainError(
            code="CONFIGURATION_INVALID",
            message="生产环境不得启用调试模式",
        )
    if not settings.web_origin.startswith("https://"):
        raise DomainError(
            code="CONFIGURATION_INVALID",
            message="生产环境 WEB_ORIGIN 必须使用 HTTPS",
        )
