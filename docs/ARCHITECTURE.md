# IntervAI Architecture

The project is intentionally split into a React/Vite frontend and a FastAPI backend.
The evaluator-facing contract lives entirely behind the backend's `/api/interview` route.

Later commits will add candidate analysis, adaptive question strategy, LLM evaluation,
knowledge-map scoring, memory management, and final feedback generation.
