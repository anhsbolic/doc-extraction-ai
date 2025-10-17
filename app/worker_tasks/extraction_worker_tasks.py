from app.services.pdfplumber_extractor import extract_chunk_pdf_to_jsonl


def extract_chunk_pdfplumber_task(payload: dict) -> dict:
    """
    payload example:
    {
      "doc_id": "...",
      "chunk_index": 1,
      "chunk_pdf_key": "docs/{doc_id}/chunks/chunk-0001.pdf",
      "out_jsonl_key": "docs/{doc_id}/texts/chunk-0001.jsonl",
      "page_offset": 1
    }
    """
    return extract_chunk_pdf_to_jsonl(
        doc_id=payload["doc_id"],
        chunk_index=payload["chunk_index"],
        chunk_pdf_key=payload["chunk_pdf_key"],
        out_jsonl_key=payload["out_jsonl_key"],
        page_offset=payload["page_offset"],
    )
