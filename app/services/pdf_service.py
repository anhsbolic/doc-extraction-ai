import io

from pypdf import PdfReader, PdfWriter


def validate_pdf_bytes(raw: bytes, max_bytes: int):
    if not raw:
        raise ValueError("Empty file")
    if len(raw) > max_bytes:
        raise ValueError("File exceeds size limit")


def split_pdf_bytes(raw: bytes, start_page: int, end_page: int):
    try:
        reader = PdfReader(io.BytesIO(raw))
    except Exception:
        raise ValueError("Invalid PDF")

    total = len(reader.pages)
    if start_page < 1 or end_page < 1 or start_page > end_page:
        raise ValueError("Invalid page range")
    if start_page > total:
        raise ValueError(f"start_page > total_pages ({total})")
    end_page = min(end_page, total)

    writer = PdfWriter()
    for i in range(start_page - 1, end_page):
        writer.add_page(reader.pages[i])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue(), total, start_page, end_page
