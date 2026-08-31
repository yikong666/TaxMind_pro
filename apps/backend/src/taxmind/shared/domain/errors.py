from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class DomainError(Exception):
    """Expected business/application error without any HTTP dependency."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: Mapping[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})
        self.retryable = retryable
