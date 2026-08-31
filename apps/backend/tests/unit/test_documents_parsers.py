from __future__ import annotations

import pytest

from taxmind.modules.documents.application.parsers import parse_uploaded_document
from taxmind.shared.domain.errors import DomainError


def test_plain_text_parser_preserves_article_boundaries_for_draft_chunks() -> None:
    parsed = parse_uploaded_document(
        content=(
            "关于虚构测试事项的公告\n\n"
            "第一条 本公告仅用于自动化测试。\n"
            "第二条 本公告自发布之日起执行。\n"
        ).encode(),
        mime_type="text/plain",
        filename="virtual-policy.txt",
    )

    assert parsed.normalized_text == (
        "关于虚构测试事项的公告\n\n第一条 本公告仅用于自动化测试。\n第二条 本公告自发布之日起执行。"
    )
    assert [chunk.content_text for chunk in parsed.chunks] == [
        "第一条 本公告仅用于自动化测试。",
        "第二条 本公告自发布之日起执行。",
    ]
    assert [chunk.chunk_type for chunk in parsed.chunks] == ["article", "article"]


def test_parser_rejects_file_extension_that_conflicts_with_declared_mime_type() -> None:
    with pytest.raises(DomainError) as error:
        parse_uploaded_document(
            content=b"plain text only",
            mime_type="text/plain",
            filename="misleading.pdf",
        )

    assert error.value.code == "VALIDATION_FAILED"


def test_html_parser_ignores_script_content_and_keeps_article_text() -> None:
    parsed = parse_uploaded_document(
        content=(
            b"<html><body><h1>\xe8\x99\x9a\xe6\x9e\x84\xe5\x85\xac\xe5\x91\x8a</h1>"
            b"<script>ignore_me()</script><p>\xe7\xac\xac\xe4\xb8\x80\xe6\x9d\xa1 "
            b"\xe4\xbb\x85\xe7\x94\xa8\xe4\xba\x8e\xe6\xb5\x8b\xe8\xaf\x95\xe3\x80\x82</p>"
            b"</body></html>"
        ),
        mime_type="text/html",
        filename="virtual-policy.html",
    )

    assert "ignore_me" not in parsed.normalized_text
    assert [chunk.content_text for chunk in parsed.chunks] == ["第一条 仅用于测试。"]
