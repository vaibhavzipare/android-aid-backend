# Android Aid Backend

FastAPI service that accepts an Android Studio error (plus optional project
context) and returns a structured, actionable fix plan. Currently uses a
rule-based mock analysis service (`MockLLMService`); the service layer is
designed so a real Claude-backed implementation can be swapped in later
without touching `main.py`.

## Setup

```bash
cd android_aid_backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`.

## Endpoints

- `GET /health` — liveness/version check
- `POST /analyze-error` — analyze an error and return a fix plan

## curl examples

**1) Gradle sync failed**

```bash
curl -X POST http://localhost:8000/analyze-error \
  -H "Content-Type: application/json" \
  -d '{
    "error_text": "Execution failed for task '\'':app:compileDebugKotlin'\''. Could not resolve com.example:lib:1.2.3 due to version conflict",
    "context": {"agp_version": "8.5.2", "gradle_version": "8.7", "kotlin_version": "1.9.24"}
  }'
```

**2) Compose preview error**

```bash
curl -X POST http://localhost:8000/analyze-error \
  -H "Content-Type: application/json" \
  -d '{
    "error_text": "@Preview render failed: Could not find method compositionLocalOf() in Compose runtime",
    "context": {"compose_version": "2024.09.00", "kotlin_version": "1.9.24"}
  }'
```

**3) ADB / device error**

```bash
curl -X POST http://localhost:8000/analyze-error \
  -H "Content-Type: application/json" \
  -d '{
    "error_text": "adb: device offline. Installation failed with message INSTALL_FAILED_UPDATE_INCOMPATIBLE"
  }'
```

**4) Generic unknown error**

```bash
curl -X POST http://localhost:8000/analyze-error \
  -H "Content-Type: application/json" \
  -d '{
    "error_text": "java.lang.NullPointerException at com.example.app.MainActivity.onCreate(MainActivity.kt:42)"
  }'
```

## Project structure

```
android_aid_backend/
  app/
    __init__.py
    main.py              # FastAPI app, routes, DI wiring
    schemas.py            # Pydantic v2 request/response models
    mock_llm_service.py    # Rule-based analysis (swappable LLMService)
    config.py             # Env-based settings
  requirements.txt
  .env.example
  README.md
```

## Swapping in a real LLM later

Implement a class satisfying the `LLMService` protocol in
`mock_llm_service.py` (e.g. `ClaudeLLMService` in a new
`claude_llm_service.py`), then change `get_llm_service()` in `main.py` to
return it. Read `CLAUDE_API_KEY` from `Settings` (already wired in
`config.py`).
