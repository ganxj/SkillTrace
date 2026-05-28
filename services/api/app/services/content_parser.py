import logging
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}

logging.getLogger("pypdf").setLevel(logging.ERROR)


async def extract_upload_text(file: UploadFile) -> str:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, Markdown, and TXT files are supported.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if suffix in {".md", ".txt"}:
        return _decode_text(data)
    if suffix == ".pdf":
        return _extract_pdf_text(data)
    return _extract_docx_text(data)


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="Could not decode text file.")


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        outline = _extract_pdf_outline(reader)
        body = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if outline:
            return f"PDF目录：\n{outline}\n\nPDF正文：\n{body}".strip()
        return body
    except Exception as exc:  # pragma: no cover - third-party parser details vary.
        raise HTTPException(status_code=400, detail=f"Could not parse PDF: {exc}") from exc


def _extract_pdf_outline(reader: object) -> str:
    try:
        outline = getattr(reader, "outline", [])
    except Exception:
        return ""

    lines: list[str] = []

    def walk(items: list, depth: int = 0) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
                continue
            title = getattr(item, "title", None) or item.get("/Title") if isinstance(item, dict) else None
            if title:
                lines.append(f"{'  ' * depth}- {title}")

    try:
        walk(outline)
    except Exception:
        return ""
    return "\n".join(lines[:300])


def _extract_docx_text(data: bytes) -> str:
    try:
        from docx import Document

        document = Document(BytesIO(data))
        return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()
    except Exception as exc:  # pragma: no cover - third-party parser details vary.
        raise HTTPException(status_code=400, detail=f"Could not parse DOCX: {exc}") from exc
