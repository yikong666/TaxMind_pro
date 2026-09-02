from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from pytest import MonkeyPatch


def _module() -> ModuleType:
    path = Path(__file__).resolve().parents[4] / "scripts" / "download_official_sample.py"
    spec = importlib.util.spec_from_file_location("official_sample_download", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Headers:
    def get_content_type(self) -> str:
        return "text/html"


class _Response:
    headers = _Headers()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def geturl(self) -> str:
        return "https://official.example/policy"

    def read(self, amount: int = -1) -> bytes:
        del amount
        return b"<!doctype html><html><body>official sample</body></html>"


def test_approved_manifest_download_records_hash_and_receipt(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    module = _module()
    monkeypatch.setattr(module, "urlopen", lambda request, timeout: _Response())
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "official-policy",
                        "url": "https://official.example/policy",
                        "expected_format": "html",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    receipts = module.download_manifest(manifest, tmp_path / "output", delay_seconds=0)

    assert receipts[0].status == "downloaded"
    assert receipts[0].sha256 is not None
    assert (tmp_path / "output" / "official-policy.html").is_file()
    receipt_json = json.loads((tmp_path / "output" / "receipt.json").read_text(encoding="utf-8"))
    assert receipt_json[0]["source_url"] == "https://official.example/policy"


def test_download_rejects_non_https_source(tmp_path: Path) -> None:
    module = _module()
    receipt = module._download_item(
        {"id": "unsafe", "url": "http://official.example/policy", "expected_format": "html"},
        tmp_path,
    )

    assert receipt.status == "failed"
    assert receipt.failure_reason == "source URL must use HTTPS"
