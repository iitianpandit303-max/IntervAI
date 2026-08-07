# Evaluator API Contract

IntervAI preserves the supplied evaluator contract exactly at the public boundary.

## Start

`POST /api/interview`

```json
{
  "sessionId": "abc-123",
  "candidate": { "...": "provided candidate object" }
}
```

Response:

```json
{
  "reply": "...",
  "done": false,
  "feedback": null
}
```

## Continue

```json
{
  "sessionId": "abc-123",
  "message": "candidate answer"
}
```

## Complete

```json
{
  "reply": "Interview completed.",
  "done": true,
  "feedback": {
    "summary": "...",
    "strengths": [],
    "gaps": [],
    "next": []
  }
}
```

The current question engine is deterministic and mocked. LLM/adaptive behavior is intentionally deferred.
