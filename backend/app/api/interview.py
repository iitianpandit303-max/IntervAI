from fastapi import APIRouter, HTTPException

from app.models.api import InterviewRequest, InterviewResponse
from app.services.interview_orchestrator import InterviewOrchestrator


router = APIRouter(tags=["interview"])
orchestrator = InterviewOrchestrator()


@router.post("/api/interview", response_model=InterviewResponse)
def interview(payload: InterviewRequest) -> InterviewResponse:
    if payload.candidate is not None:
        try:
            return orchestrator.start(payload.sessionId, payload.candidate)
        except ValueError as exc:
            if str(exc) == "session_exists":
                raise HTTPException(status_code=409, detail="Session already exists.") from exc
            raise

    try:
        return orchestrator.continue_interview(payload.sessionId, payload.message or "")
    except ValueError as exc:
        if str(exc) == "session_not_found":
            raise HTTPException(status_code=404, detail="Interview session not found.") from exc
        raise
