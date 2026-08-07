from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.interview import router as interview_router


app = FastAPI(
    title="IntervAI API",
    version="0.4.0",
    description="ABTalks AI Cohort adaptive technical interview backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
