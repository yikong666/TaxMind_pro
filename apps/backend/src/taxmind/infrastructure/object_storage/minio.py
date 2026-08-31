from __future__ import annotations

import asyncio
import hmac
import io
from typing import BinaryIO, Protocol

from minio import Minio
from minio.error import S3Error

from taxmind.bootstrap.settings import Settings
from taxmind.shared.domain.errors import DomainError


class MinioClient(Protocol):
    def stat_object(self, bucket_name: str, object_name: str) -> object: ...

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "",
        metadata: dict[str, str | list[str] | tuple[str]] | None = None,
    ) -> object: ...


def create_minio_object_store(settings: Settings) -> MinioObjectStore:
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key.get_secret_value(),
        secret_key=settings.minio_secret_key.get_secret_value(),
        secure=settings.minio_secure,
    )
    return MinioObjectStore(client)


class MinioObjectStore:
    def __init__(self, client: MinioClient) -> None:
        self._client = client

    async def put_immutable(
        self,
        bucket: str,
        key: str,
        content: bytes,
        mime_type: str,
        sha256: str,
    ) -> None:
        await asyncio.to_thread(
            self._put_immutable,
            bucket,
            key,
            content,
            mime_type,
            sha256,
        )

    def _put_immutable(
        self,
        bucket: str,
        key: str,
        content: bytes,
        mime_type: str,
        sha256: str,
    ) -> None:
        try:
            stat = self._client.stat_object(bucket, key)
        except S3Error as error:
            if error.code not in {"NoSuchKey", "NoSuchObject"}:
                raise
        else:
            existing_hash = _object_metadata_hash(stat)
            existing_size = getattr(stat, "size", None)
            if (
                isinstance(existing_size, int)
                and existing_size == len(content)
                and existing_hash is not None
                and hmac.compare_digest(existing_hash, sha256)
            ):
                return
            raise DomainError(code="RESOURCE_CONFLICT", message="原始文件对象键已被不同内容占用")
        self._client.put_object(
            bucket,
            key,
            io.BytesIO(content),
            len(content),
            content_type=mime_type,
            metadata={"sha256": sha256},
        )


def _object_metadata_hash(stat: object) -> str | None:
    metadata = getattr(stat, "metadata", None)
    if not isinstance(metadata, dict):
        return None
    for key, value in metadata.items():
        if key.casefold() in {"sha256", "x-amz-meta-sha256"} and isinstance(value, str):
            return value
    return None
