from fastapi import APIRouter
from pydantic import BaseModel

from app.services.docs_extraction_pipeline import plan_pdfplumber_extraction_jobs

router = APIRouter(prefix="/docs/extract", tags=["docs-extract"])


class PlanResponse(BaseModel):
    doc_id: str
    total_jobs: int
    jobs: list


@router.post("/{doc_id}/async", response_model=PlanResponse)
def extract_pdfplumber_async(doc_id: str):
    plan = plan_pdfplumber_extraction_jobs(doc_id)
    return plan
