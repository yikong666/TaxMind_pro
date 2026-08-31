from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from ipaddress import ip_address
from pathlib import PurePath
from typing import Protocol
from urllib.parse import urlparse

from taxmind.modules.sources.domain import IngestionJobRecord, SourceSiteRecord
from taxmind.modules.sources.infrastructure.repository import SqlAlchemySourcesRepository
from taxmind.modules.sources.infrastructure.uow import SqlAlchemySourcesUnitOfWork
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal

_SOURCE_LEVELS = frozenset({"A", "B", "C", "D"})
_COLLECTION_METHODS = frozenset({"manual", "whitelist_crawl", "api", "file_import"})
_MANUAL_UPLOAD_EXTENSIONS = frozenset({".htm", ".html", ".pdf", ".txt"})
_RESTRICTED_RULE_KEY_PARTS = frozenset(
    {
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "cookie",
        "credential",
        "password",
        "secret",
        "token",
    }
)


class SourcesUnitOfWorkFactory(Protocol):
    def __call__(self) -> SqlAlchemySourcesUnitOfWork: ...


@dataclass(frozen=True, slots=True)
class RegisterSourceSiteCommand:
    name: str
    base_url: str
    source_level: str
    authority_name: str
    region_code: str
    collection_method: str
    whitelist_rules: dict[str, object]
    crawl_interval_minutes: int | None
    request_id: str


@dataclass(frozen=True, slots=True)
class CreateManualUploadJobCommand:
    source_site_id: str
    filename: str
    content_hash_sha256: str
    request_id: str


@dataclass(frozen=True, slots=True)
class CreatedIngestionJob:
    job: IngestionJobRecord
    created: bool


class SourcesService:
    def __init__(self, *, uow_factory: SourcesUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def register_source(
        self, command: RegisterSourceSiteCommand, principal: Principal
    ) -> SourceSiteRecord:
        _require_knowledge_write(principal)
        name = _normalized_text(command.name, "来源名称")
        authority_name = _normalized_text(command.authority_name, "主管机关")
        base_url, domain = _validated_base_url(command.base_url)
        _validate_region_code(command.region_code)
        if command.source_level not in _SOURCE_LEVELS:
            raise DomainError(code="VALIDATION_FAILED", message="来源等级无效")
        if command.collection_method not in _COLLECTION_METHODS:
            raise DomainError(code="VALIDATION_FAILED", message="采集方式无效")
        _validate_whitelist_rules(command.whitelist_rules)
        crawl_interval = _validated_crawl_interval(
            command.collection_method,
            command.crawl_interval_minutes,
        )
        now = datetime.now(UTC)
        source = SourceSiteRecord(
            id=new_id(),
            name=name,
            base_url=base_url,
            domain=domain,
            source_level=command.source_level,
            authority_name=authority_name,
            region_code=command.region_code,
            collection_method=command.collection_method,
            whitelist_rules=dict(command.whitelist_rules),
            crawl_interval_minutes=crawl_interval,
            status="draft",
            last_checked_at=None,
            created_by=principal.user_id,
            created_at=now,
            updated_at=now,
        )
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            if await repository.get_by_scope(domain, command.region_code) is not None:
                raise DomainError(
                    code="RESOURCE_CONFLICT",
                    message="该地区下已登记相同官方来源域名",
                )
            await repository.create_source(source)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.source.registered_draft",
                resource_id=source.id,
                request_id=command.request_id,
                occurred_at=now,
            )
            await uow.commit()
        return source

    async def list_sources(self, principal: Principal) -> list[SourceSiteRecord]:
        _require_knowledge_read(principal)
        async with self._uow_factory() as uow:
            return await _repository(uow).list_sources()

    async def get_job(self, job_id: str, principal: Principal) -> IngestionJobRecord:
        _require_knowledge_read(principal)
        async with self._uow_factory() as uow:
            job = await _repository(uow).get_job(job_id)
            if job is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="导入任务不存在")
            return job

    async def create_manual_upload_job(
        self,
        command: CreateManualUploadJobCommand,
        principal: Principal,
    ) -> CreatedIngestionJob:
        _require_knowledge_write(principal)
        _, extension = _validated_upload_filename(command.filename)
        content_hash = _validated_sha256(command.content_hash_sha256)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            source = await repository.get_source(command.source_site_id)
            if source is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="知识来源不存在")
            dedupe_key = f"manual_file_import:{source.id}:{content_hash}"
            existing = await repository.get_job_by_dedupe_key(dedupe_key)
            if existing is not None:
                return CreatedIngestionJob(job=existing, created=False)
            job_id = new_id()
            job = IngestionJobRecord(
                id=job_id,
                source_site_id=source.id,
                job_type="manual_file_import",
                trigger_type="api",
                source_url=source.base_url,
                input_object_key=f"{source.id}/{job_id}/raw/{content_hash}{extension}",
                dedupe_key=dedupe_key,
                status="queued",
                attempt_count=0,
                discovered_count=0,
                changed_count=0,
                error_code=None,
                error_detail_safe=None,
                started_at=None,
                finished_at=None,
                created_by=principal.user_id,
                created_at=now,
                updated_at=now,
            )
            await repository.create_job(job)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.ingestion_job.created",
                resource_id=job.id,
                request_id=command.request_id,
                occurred_at=now,
            )
            await uow.commit()
        return CreatedIngestionJob(job=job, created=True)

    async def mark_job_succeeded(
        self,
        job_id: str,
        request_id: str,
        principal: Principal,
    ) -> IngestionJobRecord:
        _require_knowledge_write(principal)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            job = await repository.get_job(job_id, lock=True)
            if job is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="导入任务不存在")
            if job.status == "succeeded":
                return job
            if job.status != "queued":
                raise DomainError(code="RESOURCE_CONFLICT", message="导入任务当前状态不可完成")
            succeeded = replace(
                job,
                status="succeeded",
                attempt_count=job.attempt_count + 1,
                discovered_count=1,
                changed_count=1,
                started_at=job.started_at or now,
                finished_at=now,
                updated_at=now,
            )
            await repository.update_job(succeeded)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.ingestion_job.succeeded",
                resource_id=job.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
        return succeeded

    async def mark_job_failed(
        self,
        job_id: str,
        error_code: str,
        error_detail_safe: str,
        request_id: str,
        principal: Principal,
    ) -> IngestionJobRecord:
        _require_knowledge_write(principal)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            job = await repository.get_job(job_id, lock=True)
            if job is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="导入任务不存在")
            if job.status == "succeeded":
                return job
            failed = replace(
                job,
                status="failed",
                attempt_count=job.attempt_count + 1,
                error_code=_normalized_text(error_code, "导入错误码"),
                error_detail_safe=_normalized_text(error_detail_safe, "导入错误说明"),
                started_at=job.started_at or now,
                finished_at=now,
                updated_at=now,
            )
            await repository.update_job(failed)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.ingestion_job.failed",
                resource_id=job.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
        return failed


def _repository(uow: SqlAlchemySourcesUnitOfWork) -> SqlAlchemySourcesRepository:
    if uow.repository is None:
        raise RuntimeError("unit of work repository is unavailable")
    return uow.repository


def _require_knowledge_read(principal: Principal) -> None:
    if not principal.has_permission("knowledge:read"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无知识来源查看权限")


def _require_knowledge_write(principal: Principal) -> None:
    if not principal.has_permission("knowledge:write"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无知识来源维护权限")


def _normalized_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise DomainError(code="VALIDATION_FAILED", message=f"{field_name}不能为空")
    return normalized


def _validated_base_url(value: str) -> tuple[str, str]:
    normalized = value.strip()
    parsed = urlparse(normalized)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
        or parsed.query
        or parsed.fragment
    ):
        raise DomainError(
            code="VALIDATION_FAILED",
            message="官方来源必须使用不含凭据、查询参数和片段的 HTTPS 地址",
        )
    domain = parsed.hostname.encode("idna").decode("ascii").lower()
    if domain == "localhost" or _is_ip_address(domain):
        raise DomainError(code="VALIDATION_FAILED", message="官方来源不能使用本机或 IP 地址")
    normalized_path = parsed.path.rstrip("/")
    base_url = f"https://{domain}{normalized_path}" if normalized_path else f"https://{domain}"
    return base_url, domain


def _is_ip_address(value: str) -> bool:
    try:
        ip_address(value)
    except ValueError:
        return False
    return True


def _validate_region_code(value: str) -> None:
    if len(value) != 6 or not value.isdigit():
        raise DomainError(code="VALIDATION_FAILED", message="地区必须使用六位 GB/T 2260 代码")


def _validate_whitelist_rules(value: dict[str, object]) -> None:
    pending: list[object] = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            for key, child in item.items():
                normalized_key = key.casefold().replace("-", "_")
                if any(part in normalized_key for part in _RESTRICTED_RULE_KEY_PARTS):
                    raise DomainError(
                        code="VALIDATION_FAILED",
                        message="白名单规则不得包含凭据、Cookie、Token 或密钥",
                    )
                pending.append(child)
        elif isinstance(item, list):
            pending.extend(item)


def _validated_crawl_interval(method: str, value: int | None) -> int | None:
    if method == "whitelist_crawl":
        if value is None or value < 60:
            raise DomainError(
                code="VALIDATION_FAILED",
                message="白名单低频检查间隔不得少于 60 分钟",
            )
        return value
    if value is not None:
        raise DomainError(
            code="VALIDATION_FAILED",
            message="仅白名单低频检查来源可设置采集间隔",
        )
    return None


def _validated_upload_filename(value: str) -> tuple[str, str]:
    filename = value.strip()
    if not filename or PurePath(filename).name != filename:
        raise DomainError(code="VALIDATION_FAILED", message="导入文件名无效")
    extension = PurePath(filename).suffix.lower()
    if extension not in _MANUAL_UPLOAD_EXTENSIONS:
        raise DomainError(code="VALIDATION_FAILED", message="导入文件格式暂不支持")
    return filename, extension


def _validated_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise DomainError(code="VALIDATION_FAILED", message="文件哈希必须是 SHA-256 十六进制摘要")
    return normalized
