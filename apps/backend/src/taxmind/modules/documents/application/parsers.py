from __future__ import annotations

import io
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import PurePath

from taxmind.shared.domain.errors import DomainError

_ARTICLE_PATTERN = re.compile(r"^第[一二三四五六七八九十百千万零0-9]+条")
_SUPPORTED_MIME_BY_EXTENSION = {
    ".html": "text/html",
    ".htm": "text/html",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}


@dataclass(frozen=True, slots=True)
class ParsedChunk:
    chunk_type: str
    heading_path: str
    clause_label: str | None
    content_text: str


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    normalized_text: str
    chunks: list[ParsedChunk]
    warnings: list[str]


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style"}:
            self._ignored_depth += 1
        elif self._ignored_depth == 0 and tag in {
            "article",
            "br",
            "div",
            "h1",
            "h2",
            "h3",
            "h4",
            "li",
            "p",
            "section",
            "table",
            "tr",
        }:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_depth > 0:
            self._ignored_depth -= 1
        elif self._ignored_depth == 0 and tag in {
            "article",
            "div",
            "h1",
            "h2",
            "h3",
            "h4",
            "li",
            "p",
            "section",
            "table",
            "tr",
        }:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0:
            self._parts.append(data)

    @property
    def text(self) -> str:
        return "".join(self._parts)


def parse_uploaded_document(*, content: bytes, mime_type: str, filename: str) -> ParsedDocument:
    normalized_mime, extension = _validated_file_type(mime_type, filename)
    if not content:
        raise DomainError(code="VALIDATION_FAILED", message="导入文件不能为空")
    if normalized_mime == "text/plain":
        raw_text = _decode_text(content)
    elif normalized_mime == "text/html":
        extractor = _TextExtractor()
        extractor.feed(_decode_text(content))
        extractor.close()
        raw_text = extractor.text
    else:
        raw_text = _extract_pdf_text(content)
    normalized_text = _normalize_text(raw_text)
    if not normalized_text:
        raise DomainError(code="VALIDATION_FAILED", message="文件未解析出可引用文本")
    chunks = _article_chunks(normalized_text)
    if not chunks:
        chunks = _paragraph_chunks(normalized_text)
    warnings = ["pdf_text_layer_only"] if extension == ".pdf" else []
    return ParsedDocument(normalized_text=normalized_text, chunks=chunks, warnings=warnings)


def _validated_file_type(mime_type: str, filename: str) -> tuple[str, str]:
    safe_name = PurePath(filename).name
    if safe_name != filename or not safe_name.strip():
        raise DomainError(code="VALIDATION_FAILED", message="文件名无效")
    extension = PurePath(safe_name).suffix.lower()
    expected_mime = _SUPPORTED_MIME_BY_EXTENSION.get(extension)
    normalized_mime = mime_type.split(";", maxsplit=1)[0].strip().lower()
    if expected_mime is None or normalized_mime != expected_mime:
        raise DomainError(
            code="VALIDATION_FAILED",
            message="文件扩展名与 MIME 类型不匹配或暂不支持",
        )
    return normalized_mime, extension


def _decode_text(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DomainError(
            code="VALIDATION_FAILED",
            message="文本文件必须使用 UTF-8 编码",
        ) from error


def _extract_pdf_text(content: bytes) -> str:
    if not content.startswith(b"%PDF-"):
        raise DomainError(code="VALIDATION_FAILED", message="PDF 文件签名无效")
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except DomainError:
        raise
    except Exception as error:
        raise DomainError(code="VALIDATION_FAILED", message="PDF 文本层解析失败") from error


def _normalize_text(value: str) -> str:
    lines = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    normalized_lines: list[str] = []
    previous_blank = False
    for line in lines:
        normalized_line = " ".join(line.split())
        if not normalized_line:
            if normalized_lines and not previous_blank:
                normalized_lines.append("")
            previous_blank = True
            continue
        normalized_lines.append(normalized_line)
        previous_blank = False
    return "\n".join(normalized_lines).strip()


def _article_chunks(text: str) -> list[ParsedChunk]:
    chunks: list[ParsedChunk] = []
    current_lines: list[str] = []
    current_label: str | None = None
    for line in text.splitlines():
        if _ARTICLE_PATTERN.match(line):
            if current_label is not None:
                chunks.append(_article_chunk(current_label, current_lines))
            current_label = line.split(maxsplit=1)[0]
            current_lines = [line]
        elif current_label is not None:
            current_lines.append(line)
    if current_label is not None:
        chunks.append(_article_chunk(current_label, current_lines))
    return chunks


def _article_chunk(label: str, lines: list[str]) -> ParsedChunk:
    content_text = "\n".join(line for line in lines if line).strip()
    return ParsedChunk(
        chunk_type="article",
        heading_path=label,
        clause_label=label,
        content_text=content_text,
    )


def _paragraph_chunks(text: str) -> list[ParsedChunk]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    return [
        ParsedChunk(
            chunk_type="paragraph",
            heading_path="导入正文",
            clause_label=None,
            content_text=paragraph,
        )
        for paragraph in paragraphs
    ]
