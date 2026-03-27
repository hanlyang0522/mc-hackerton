"""자소서 생성 API 엔드포인트."""
import traceback
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..pipeline import CoverLetterPipeline

router = APIRouter()


class QuestionInput(BaseModel):
    text: str
    max_length: int = 500


class GenerateRequest(BaseModel):
    company: str
    position: str
    questions: List[QuestionInput]


class QuestionResultResponse(BaseModel):
    question: str
    question_type: Optional[str]
    material_display: str
    material_id: str
    draft: str
    char_count: int
    score: int


class GenerateResponse(BaseModel):
    company: str
    position: str
    results: List[QuestionResultResponse]


class ErrorResponse(BaseModel):
    error: str


@router.post("/generate")
def generate(req: GenerateRequest):
    """자소서 생성 API."""
    try:
        pipeline = CoverLetterPipeline()
        output = pipeline.run(
            company=req.company,
            position=req.position,
            questions=[q.text for q in req.questions],
            max_lengths=[q.max_length for q in req.questions],
        )

        return GenerateResponse(
            company=output.company,
            position=output.position,
            results=[
                QuestionResultResponse(
                    question=r.question,
                    question_type=r.question_type,
                    material_display=r.material_display,
                    material_id=r.material_id,
                    draft=r.draft,
                    char_count=r.char_count,
                    score=r.score,
                )
                for r in output.results
            ],
        )
    except Exception as exc:
        traceback.print_exc()
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"error": str(exc)})
