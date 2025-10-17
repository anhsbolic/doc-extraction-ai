import time
from typing import List, Dict, Any

import pdfplumber

from app.services.storage import BUCKET, get_object_to_tempfile, put_jsonl_lines

DEFAULT_TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "intersection_tolerance": 5,
    "snap_tolerance": 3,
    "edge_min_length": 3,
}


def _tables_to_markdown(tables: List[List[List[str]]]) -> List[Dict[str, Any]]:
    md_tables = []
    for t in tables:
        if not t:
            continue
        # asumsi baris pertama = header
        header = [str(x).strip() if x is not None else "" for x in t[0]]
        rows = [[str(x).strip() if x is not None else "" for x in r] for r in t[1:]]
        # build markdown
        header_line = "| " + " | ".join(header) + " |"
        sep_line = "| " + " | ".join([":--" for _ in header]) + " |"
        row_lines = ["| " + " | ".join(r) + " |" for r in rows]
        md = "\n".join([header_line, sep_line] + row_lines)
        md_tables.append({"title": None, "markdown": md, "header": header, "rows": rows})
    return md_tables


def _build_combined_markdown(text_blocks: List[Dict[str, str]], tables_md: List[Dict[str, Any]]) -> str:
    parts = []
    if text_blocks:
        parts.append("\n\n".join(tb["content"] for tb in text_blocks if tb.get("content")))
    for i, t in enumerate(tables_md, start=1):
        parts.append(f"### Table {i}\n{t['markdown']}")
    return "\n\n".join([p for p in parts if p])


def extract_chunk_pdf_to_jsonl(
        *,
        doc_id: str,
        chunk_index: int,
        chunk_pdf_key: str,
        out_jsonl_key: str,
        page_offset: int,  # halaman awal untuk chunk ini (1-based)
        table_settings: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Ekstrak sebuah chunk PDF menjadi JSONL (baris per halaman) dan upload ke MinIO.
    Return ringkasan meta.
    """
    t0 = time.time()
    ts: List[Dict[str, Any]] = []
    src_path = get_object_to_tempfile(BUCKET, chunk_pdf_key)

    if table_settings is None:
        table_settings = DEFAULT_TABLE_SETTINGS

    with pdfplumber.open(src_path) as pdf:
        for i, page in enumerate(pdf.pages, start=0):
            page_no = page_offset + i
            p_start = time.time()

            # extract text
            txt = page.extract_text(x_tolerance=1.5, y_tolerance=2.0) or ""
            text_blocks = []
            if txt:
                # bisa dipecah per paragraf jika mau; sekarang single block
                text_blocks = [{"type": "paragraph", "content": txt}]

            # extract tables
            raw_tables = page.extract_tables(table_settings=table_settings) or []
            tables_md = _tables_to_markdown(raw_tables)

            combined_md = _build_combined_markdown(text_blocks, tables_md)

            stats = {
                "char_count": len(txt),
                "word_count": len(txt.split()) if txt else 0,
                "tables_detected": len(raw_tables),
                "extract_duration_ms": int(1000 * (time.time() - p_start)),
            }

            ts.append({
                "doc_id": doc_id,
                "chunk_index": chunk_index,
                "page_no": page_no,
                "extract_method": "pdfplumber_mixed",
                "source_key": chunk_pdf_key,
                "text_blocks": text_blocks,
                "tables": tables_md,
                "combined_markdown": combined_md,
                "stats": stats,
                "version": "1.0.0",
            })

    put_jsonl_lines(out_jsonl_key, ts)

    return {
        "doc_id": doc_id,
        "chunk_index": chunk_index,
        "pages_written": len(ts),
        "out_jsonl_key": out_jsonl_key,
        "duration_ms": int(1000 * (time.time() - t0)),
    }
