from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.interview import router as interview_router
from app.config.settings import LLMSettings, RuntimeSettings


runtime_settings = RuntimeSettings.from_env()

app = FastAPI(
    title="IntervAI API",
    version="0.6.0",
    description="ABTalks AI Cohort adaptive technical interview backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(runtime_settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(interview_router)


@app.get("/health")
def health() -> dict[str, str]:
    llm = LLMSettings.from_env()
    return {
        "status": "ok",
        "version": app.version,
        "llmMode": "configured" if llm.enabled else "deterministic-fallback",
    }
