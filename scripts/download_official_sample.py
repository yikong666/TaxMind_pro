from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MAX_BYTES = 25 * 1024 * 1024
USER_AGENT = "TaxMind-Pro-Official-Sample/1.0 (+internal-governed-import)"


class HttpResponse(Protocol):
    def read(self, amount: int = -1) -> bytes: ...

    def geturl(self) -> str: ...

    @property
    def headers(self) -> object: ...


@dataclass(frozen=True, slots=True)
class DownloadReceipt:
    item_id: str
    source_url: str
    captured_at: str
    status: str
    filename: str | None
    content_type: str | None
    size_bytes: int | None
    sha256: str | None
    failure_reason: str | None


def download_manifest(
    manifest_path: Path, output_dir: Path, *, delay_seconds: float = 1.0
) -> list[DownloadReceipt]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("manifest must contain non-empty items")
    output_dir.mkdir(parents=True, exist_ok=True)
    receipts: list[DownloadReceipt] = []
    for index, item in enumerate(items):
        receipt = _download_item(item, output_dir)
        receipts.append(receipt)
        if index < len(items) - 1:
            time.sleep(delay_seconds)
    receipt_path = output_dir / "receipt.json"
    receipt_path.write_text(
        json.dumps([asdict(receipt) for receipt in receipts], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return receipts


def _download_item(item: object, output_dir: Path) -> DownloadReceipt:
    captured_at = datetime.now(UTC).isoformat()
    if not isinstance(item, dict):
        return DownloadReceipt(
            "unknown", "", captured_at, "failed", None, None, None, None, "invalid manifest item"
        )
    item_id = item.get("id")
    source_url = item.get("url")
    expected_format = item.get("expected_format")
    if (
        not isinstance(item_id, str)
        or not isinstance(source_url, str)
        or expected_format not in {"html", "pdf"}
    ):
        return DownloadReceipt(
            str(item_id),
            str(source_url),
            captured_at,
            "failed",
            None,
            None,
            None,
            None,
            "invalid manifest fields",
        )
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or not parsed.netloc:
        return DownloadReceipt(
            item_id,
            source_url,
            captured_at,
            "failed",
            None,
            None,
            None,
            None,
            "source URL must use HTTPS",
        )
    try:
        request = Request(  # noqa: S310 - URL is validated as HTTPS before use
            source_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.1",
            },
        )
        with urlopen(request, timeout=30) as response:  # noqa: S310 - validated HTTPS Request
            final_url = response.geturl()
            if urlparse(final_url).netloc != parsed.netloc:
                raise ValueError("redirected to an unapproved host")
            content = response.read(MAX_BYTES + 1)
            content_type = _content_type(response.headers)
        if len(content) > MAX_BYTES:
            raise ValueError("response exceeds 25 MiB limit")
        if not _matches_expected_format(content, content_type, expected_format):
            raise ValueError("response format does not match manifest")
        suffix = ".pdf" if expected_format == "pdf" else ".html"
        filename = f"{item_id}{suffix}"
        (output_dir / filename).write_bytes(content)
        return DownloadReceipt(
            item_id,
            source_url,
            captured_at,
            "downloaded",
            filename,
            content_type,
            len(content),
            sha256(content).hexdigest(),
            None,
        )
    except Exception as error:
        return DownloadReceipt(
            item_id,
            source_url,
            captured_at,
            "failed",
            None,
            None,
            None,
            None,
            _safe_error(error),
        )


def _content_type(headers: object) -> str | None:
    getter = getattr(headers, "get_content_type", None)
    return getter() if callable(getter) else None


def _matches_expected_format(
    content: bytes, content_type: str | None, expected_format: str
) -> bool:
    if expected_format == "pdf":
        return content.startswith(b"%PDF-") and content_type in {
            "application/pdf",
            "application/octet-stream",
        }
    normalized = content.lstrip().lower()
    return content_type == "text/html" and (
        normalized.startswith(b"<!doctype html") or normalized.startswith(b"<html")
    )


def _safe_error(error: Exception) -> str:
    message = str(error).replace("\n", " ").strip()
    return (message or error.__class__.__name__)[:200]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download an approved, low-frequency official sample."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    receipts = download_manifest(args.manifest, args.output_dir)
    failed = [receipt for receipt in receipts if receipt.status != "downloaded"]
    print(json.dumps([asdict(receipt) for receipt in receipts], ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
