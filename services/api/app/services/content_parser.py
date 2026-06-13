import base64
import logging
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}
MAX_IMAGE_BYTES = 2_000_000
MAX_RAW_IMAGE_BYTES = 20_000_000
MAX_IMAGES_PER_FILE = 60

logging.getLogger("pypdf").setLevel(logging.ERROR)


@dataclass
class ExtractedImage:
    page_number: int
    name: str
    mime_type: str
    data_url: str


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    images: list[ExtractedImage] = field(default_factory=list)


@dataclass
class ExtractedContent:
    text: str
    pages: list[ExtractedPage]
    images: list[ExtractedImage]


async def extract_upload_content(file: UploadFile) -> ExtractedContent:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, Markdown, and TXT files are supported.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if suffix in {".md", ".txt"}:
        text = _decode_text(data)
        return ExtractedContent(text=text, pages=[ExtractedPage(page_number=1, text=text)], images=[])
    if suffix == ".pdf":
        return _extract_pdf_content(data)
    text = _extract_docx_text(data)
    return ExtractedContent(text=text, pages=[ExtractedPage(page_number=1, text=text)], images=[])


async def extract_upload_text(file: UploadFile) -> str:
    return (await extract_upload_content(file)).text


def _sanitize_text(text: str) -> str:
    """Remove null bytes and other problematic characters for PostgreSQL."""
    return text.replace("\x00", "")


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return _sanitize_text(data.decode(encoding).strip())
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="Could not decode text file.")


def _extract_pdf_content(data: bytes) -> ExtractedContent:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        outline = _extract_pdf_outline(reader)
        pages: list[ExtractedPage] = []
        images: list[ExtractedImage] = []
        image_count = 0
        for index, page in enumerate(reader.pages, start=1):
            page_images: list[ExtractedImage] = []
            if image_count < MAX_IMAGES_PER_FILE:
                try:
                    raw_images = getattr(page, "images", []) or []
                except Exception:
                    raw_images = []
                for image in raw_images:
                    try:
                        if image_count >= MAX_IMAGES_PER_FILE:
                            break
                        extracted = _image_to_data_url(image, index)
                        if extracted is None:
                            continue
                        page_images.append(extracted)
                        images.append(extracted)
                        image_count += 1
                    except Exception:
                        continue
            pages.append(
                ExtractedPage(
                    page_number=index,
                    text=_sanitize_text((page.extract_text() or "").strip()),
                    images=page_images,
                )
            )
        body = "\n\n".join(f"[第{page.page_number}页]\n{page.text}" for page in pages if page.text).strip()
        if outline:
            text = _sanitize_text(f"PDF目录：\n{outline}\n\nPDF正文：\n{body}".strip())
        else:
            text = _sanitize_text(body)
        return ExtractedContent(text=text, pages=pages, images=images)
    except Exception as exc:  # pragma: no cover - third-party parser details vary.
        raise HTTPException(status_code=400, detail=f"Could not parse PDF: {exc}") from exc


def _image_to_data_url(image: object, page_number: int) -> ExtractedImage | None:
    data = getattr(image, "data", b"") or b""
    if not data or len(data) > MAX_RAW_IMAGE_BYTES:
        return None
    name = str(getattr(image, "name", "") or f"page_{page_number}_image")
    jpeg_data = _to_jpeg(data)
    if jpeg_data is None:
        return None
    encoded = base64.b64encode(jpeg_data).decode("ascii")
    return ExtractedImage(
        page_number=page_number,
        name=f"{Path(name).stem or 'image'}.jpg",
        mime_type="image/jpeg",
        data_url=f"data:image/jpeg;base64,{encoded}",
    )


def _to_jpeg(data: bytes) -> bytes | None:
    try:
        from PIL import Image

        with Image.open(BytesIO(data)) as image:
            rgb = image.convert("RGB")
            if max(rgb.size) > 1024:
                rgb.thumbnail((1024, 1024))
            output = BytesIO()
            rgb.save(output, format="JPEG", quality=75, optimize=True, progressive=True)
            jpeg_data = output.getvalue()
            if len(jpeg_data) <= MAX_IMAGE_BYTES:
                return jpeg_data

            rgb = image.convert("RGB")
            rgb.thumbnail((768, 768))
            output = BytesIO()
            rgb.save(output, format="JPEG", quality=60, optimize=True, progressive=True)
            return output.getvalue()
    except Exception:
        return None


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
        return _sanitize_text("\n".join(paragraph.text for paragraph in document.paragraphs).strip())
    except Exception as exc:  # pragma: no cover - third-party parser details vary.
        raise HTTPException(status_code=400, detail=f"Could not parse DOCX: {exc}") from exc
