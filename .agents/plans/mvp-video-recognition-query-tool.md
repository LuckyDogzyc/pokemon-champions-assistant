# MVP Video Recognition Query Tool Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build the first working version of Pokemon Champions Assistant that reads a capture-card video source, recognizes the names of the two active on-screen Pokémon in Chinese, and shows linked Pokémon info plus type matchup data in a second-window web UI.

**Architecture:** Use a local-first split architecture: Next.js frontend for the second-window UI, FastAPI backend for data/query APIs and recognition orchestration, and a Python/OpenCV-based capture + recognition pipeline. Recognition is intentionally limited to the two active battlefield names, with manual override as a required fallback.

**Tech Stack:** Next.js 15 + React + TypeScript, FastAPI + Pydantic, Python 3.11, OpenCV, Chinese-first OCR adapter interface, local JSON data files, pytest, vitest.

---

## Scope Lock

This plan implements only the MVP defined in `PRD.md`:
- Capture-card real-time input
- Recognize **both current on-field Pokémon names**
- Chinese-first recognition
- Pokémon info lookup
- Type matchup lookup
- Manual override when recognition is wrong
- Browser-based second-window UI

Not in this plan:
- Damage calculator
- Team recommender
- Full battle state parsing
- Automated strategic advice
- Multi-language OCR shipping in v1

---

## Required Project Structure

Target repo root:

```text
pokemon-champions-assistant/
  frontend/
  backend/
  data/
  tests/
  .agents/plans/
  PRD.md
  CLAUDE.md
```

Backend target structure:

```text
backend/
  app/
    api/
    core/
    models/
    services/
    schemas/
    main.py
  tests/
```

Frontend target structure:

```text
frontend/
  app/
  components/
  lib/
  types/
  tests/
```

Data target structure:

```text
data/
  pokemon/
    pokemon_zh_index.json
    type_chart.json
    aliases_zh.json
```

---

## External References To Check During Execution

- OpenCV Python docs: video capture APIs
- FastAPI docs: background tasks / dependency injection / response models
- Next.js app router docs
- OCR library docs for Chinese support (start with PaddleOCR evaluation, but keep adapter pluggable)

---

## Implementation Strategy

1. Scaffold backend and frontend first.
2. Add static data loading and query APIs.
3. Add video-source enumeration and frame capture.
4. Add a minimal recognition pipeline with a mock recognizer first.
5. Replace mock recognizer with Chinese OCR adapter wiring.
6. Add polling/current-state endpoints.
7. Build second-window UI.
8. Add manual override flow.
9. Add verification commands and integration checks.

---

## Step by Step Tasks

### Task 1: Create backend Python project skeleton

**Objective:** Establish the FastAPI backend structure and dependency manifest.

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/__init__.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_health.py`

**Step 1: Write failing test**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_returns_ok():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
```

**Step 2: Run test to verify failure**

Run: `cd backend && pytest tests/test_health.py -v`
Expected: FAIL — module/app missing.

**Step 3: Write minimal implementation**

Create `backend/app/main.py` with a FastAPI app and `/api/health` route.

**Step 4: Run test to verify pass**

Run: `cd backend && pytest tests/test_health.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: scaffold backend fastapi app"
```

---

### Task 2: Create frontend Next.js skeleton

**Objective:** Establish the second-window frontend app.

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx`
- Create: `frontend/app/globals.css`
- Test: `frontend/tests/home.test.tsx`

**Step 1: Write failing test**

Create a test asserting the home page renders the product title and placeholder status text.

**Step 2: Run test to verify failure**

Run: `cd frontend && npm test -- --runInBand home.test.tsx`
Expected: FAIL — app not initialized.

**Step 3: Write minimal implementation**

Render a page title like `Pokemon Champions Assistant` and text like `Recognition idle`.

**Step 4: Run test to verify pass**

Run: `cd frontend && npm test -- --runInBand home.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend
git commit -m "feat: scaffold frontend nextjs app"
```

---

### Task 3: Add backend settings and environment support

**Objective:** Centralize backend config for ports, capture source, and recognizer mode.

**Files:**
- Create: `backend/app/core/settings.py`
- Create: `backend/.env.example`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_settings.py`

**Step 1: Write failing test**

Test that settings load defaults for API title, capture poll interval, and recognizer mode.

**Step 2: Run test to verify failure**

Run: `cd backend && pytest tests/test_settings.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Use Pydantic settings with fields like:
- `APP_NAME`
- `CAPTURE_FRAME_INTERVAL_MS`
- `RECOGNIZER_MODE`
- `DEFAULT_LANGUAGE=zh`

**Step 4: Run test to verify pass**

Run: `cd backend && pytest tests/test_settings.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add backend settings"
```

---

### Task 4: Add Pokémon and type data files

**Objective:** Create the local MVP data source for info and type matchup lookup.

**Files:**
- Create: `data/pokemon/pokemon_zh_index.json`
- Create: `data/pokemon/type_chart.json`
- Create: `data/pokemon/aliases_zh.json`
- Create: `backend/app/services/data_loader.py`
- Test: `backend/tests/test_data_loader.py`

**Step 1: Write failing test**

Test that data loader can read Pokémon entries, aliases, and type chart from `data/pokemon/`.

**Step 2: Run test to verify failure**

Run: `cd backend && pytest tests/test_data_loader.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

- Put a small seed dataset in JSON for at least 6 Pokémon and all 18 types.
- Data loader should expose functions:
  - `load_pokemon_index()`
  - `load_aliases()`
  - `load_type_chart()`

**Step 4: Run test to verify pass**

Run: `cd backend && pytest tests/test_data_loader.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add data backend
git commit -m "feat: add pokemon seed data and loaders"
```

---

### Task 5: Implement Pokémon search and detail API

**Objective:** Expose Pokémon lookup based on the local data source.

**Files:**
- Create: `backend/app/schemas/pokemon.py`
- Create: `backend/app/services/pokemon_service.py`
- Create: `backend/app/api/pokemon.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_pokemon_api.py`

**Step 1: Write failing test**

Add tests for:
- `GET /api/pokemon/search?q=喷火龙`
- `GET /api/pokemon/喷火龙`

**Step 2: Run test to verify failure**

Run: `cd backend && pytest tests/test_pokemon_api.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Search should support:
- exact Chinese name
- alias lookup
- case-insensitive fallback where relevant

**Step 4: Run test to verify pass**

Run: `cd backend && pytest tests/test_pokemon_api.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add pokemon lookup api"
```

---

### Task 6: Implement type matchup API

**Objective:** Expose single-type and dual-type matchup calculations.

**Files:**
- Create: `backend/app/schemas/types.py`
- Create: `backend/app/services/type_service.py`
- Create: `backend/app/api/types.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_types_api.py`

**Step 1: Write failing test**

Test:
- `GET /api/type/Fire/matchups`
- `POST /api/type/combined-matchups` with `['Fire', 'Flying']`

**Step 2: Run test to verify failure**

Run: `cd backend && pytest tests/test_types_api.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Return:
- offensive strengths/weaknesses
- defensive weaknesses/resistances/immunities
- combined defensive multipliers for dual types

**Step 4: Run test to verify pass**

Run: `cd backend && pytest tests/test_types_api.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add type matchup api"
```

---

### Task 7: Implement video source enumeration service

**Objective:** Detect available local video devices with capture-card-first compatibility.

**Files:**
- Create: `backend/app/schemas/video.py`
- Create: `backend/app/services/video_source_service.py`
- Create: `backend/app/api/video.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_video_sources_api.py`

**Step 1: Write failing test**

Test that `GET /api/video/sources` returns a list with a stable schema.
Mock the low-level device enumeration if direct hardware access is unavailable in tests.

**Step 2: Run test to verify failure**

Run: `cd backend && pytest tests/test_video_sources_api.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

- Add a device enumeration abstraction.
- Return fields like:
  - `id`
  - `label`
  - `backend`
  - `is_capture_card_candidate`

**Step 4: Run test to verify pass**

Run: `cd backend && pytest tests/test_video_sources_api.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add video source enumeration api"
```

---

### Task 8: Implement frame capture session service

**Objective:** Start a session against a selected video device and read frames safely.

**Files:**
- Create: `backend/app/services/capture_session.py`
- Create: `backend/app/services/frame_store.py`
- Modify: `backend/app/api/video.py`
- Test: `backend/tests/test_capture_session.py`

**Step 1: Write failing test**

Test that a capture session can be started and returns either a current frame placeholder or session state using a mocked frame source.

**Step 2: Run test to verify failure**

Run: `cd backend && pytest tests/test_capture_session.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

- Implement start/stop session methods.
- Store latest frame metadata in memory.
- Do not solve full streaming yet; one polling-friendly current-state path is enough.

**Step 4: Run test to verify pass**

Run: `cd backend && pytest tests/test_capture_session.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add frame capture session service"
```

---

### Task 9: Define recognition state models for both sides

**Objective:** Establish schemas for recognition results, confidence, and manual override state.

**Files:**
- Create: `backend/app/schemas/recognition.py`
- Create: `backend/app/models/recognition_state.py`
- Test: `backend/tests/test_recognition_models.py`

**Step 1: Write failing test**

Test serialization for:
- `player_active_name`
- `opponent_active_name`
- confidence per side
- source (`ocr`, `manual`, `mock`)
- timestamp

**Step 2: Run test to verify failure**

Run: `cd backend && pytest tests/test_recognition_models.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Create schemas/models with explicit side separation.

**Step 4: Run test to verify pass**

Run: `cd backend && pytest tests/test_recognition_models.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add recognition state schemas"
```

---

### Task 10: Implement recognizer adapter interface and mock recognizer

**Objective:** Decouple capture from OCR so the pipeline can be tested before real OCR integration.

**Files:**
- Create: `backend/app/services/recognizers/base.py`
- Create: `backend/app/services/recognizers/mock_recognizer.py`
- Create: `backend/app/services/recognition_pipeline.py`
- Test: `backend/tests/test_recognition_pipeline.py`

**Step 1: Write failing test**

Test that the pipeline takes frame input and returns recognition results for both sides using a mock recognizer.

**Step 2: Run test to verify failure**

Run: `cd backend && pytest tests/test_recognition_pipeline.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

- Define `recognize(frame) -> RecognitionState`
- Mock recognizer can return fixed names for deterministic tests.

**Step 4: Run test to verify pass**

Run: `cd backend && pytest tests/test_recognition_pipeline.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add recognition pipeline abstraction"
```

---

### Task 11: Add Chinese-first OCR adapter wiring

**Objective:** Add a pluggable OCR adapter interface that can be swapped, with Chinese-first configuration.

**Files:**
- Create: `backend/app/services/recognizers/ocr_adapter.py`
- Create: `backend/app/services/recognizers/chinese_ocr_recognizer.py`
- Modify: `backend/app/core/settings.py`
- Test: `backend/tests/test_chinese_ocr_recognizer.py`

**Step 1: Write failing test**

Test that the OCR recognizer normalizes Chinese text through alias mapping and returns both-side names when the OCR adapter yields known strings.

**Step 2: Run test to verify failure**

Run: `cd backend && pytest tests/test_chinese_ocr_recognizer.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

- Adapter contract should hide the OCR provider specifics.
- Start with dependency-injected OCR result payloads in tests.
- Normalize OCR text through `aliases_zh.json` before Pokémon lookup.

**Step 4: Run test to verify pass**

Run: `cd backend && pytest tests/test_chinese_ocr_recognizer.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend data
 git commit -m "feat: add chinese-first ocr recognizer adapter"
```

---

### Task 12: Add recognition session API

**Objective:** Expose start session and current recognition endpoints.

**Files:**
- Create: `backend/app/api/recognition.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_recognition_api.py`

**Step 1: Write failing test**

Test:
- `POST /api/recognition/session/start`
- `GET /api/recognition/current`

Use mocked capture + recognizer services.

**Step 2: Run test to verify failure**

Run: `cd backend && pytest tests/test_recognition_api.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

`/api/recognition/current` should return:
- current player-side name
- current opponent-side name
- confidence fields
- latest linked Pokémon info if lookup succeeds

**Step 4: Run test to verify pass**

Run: `cd backend && pytest tests/test_recognition_api.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add recognition session api"
```

---

### Task 13: Add manual override API

**Objective:** Ensure streamer can correct recognition without waiting on OCR.

**Files:**
- Modify: `backend/app/api/recognition.py`
- Modify: `backend/app/services/recognition_pipeline.py`
- Test: `backend/tests/test_manual_override_api.py`

**Step 1: Write failing test**

Test `POST /api/recognition/override` with payload like:

```json
{
  "side": "player",
  "name": "喷火龙"
}
```

and verify current state changes to source=`manual`.

**Step 2: Run test to verify failure**

Run: `cd backend && pytest tests/test_manual_override_api.py -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Allow override per side (`player` / `opponent`) and merge it into current recognition state.

**Step 4: Run test to verify pass**

Run: `cd backend && pytest tests/test_manual_override_api.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend
git commit -m "feat: add manual override api"
```

---

### Task 14: Add frontend API client and polling hooks

**Objective:** Frontend must fetch current recognition state and available video sources.

**Files:**
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/hooks.ts`
- Create: `frontend/types/api.ts`
- Test: `frontend/tests/api-client.test.ts`

**Step 1: Write failing test**

Test that the API client calls the expected backend endpoints and parses recognition payloads.

**Step 2: Run test to verify failure**

Run: `cd frontend && npm test -- --runInBand api-client.test.ts`
Expected: FAIL.

**Step 3: Write minimal implementation**

Add typed methods:
- `getVideoSources()`
- `startRecognitionSession()`
- `getCurrentRecognition()`
- `overrideRecognition()`
- `searchPokemon()`

**Step 4: Run test to verify pass**

Run: `cd frontend && npm test -- --runInBand api-client.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend
git commit -m "feat: add frontend api client"
```

---

### Task 15: Build second-window recognition dashboard UI

**Objective:** Render the MVP UI for live use beside OBS.

**Files:**
- Create: `frontend/components/video-source-panel.tsx`
- Create: `frontend/components/recognition-status-panel.tsx`
- Create: `frontend/components/pokemon-card.tsx`
- Create: `frontend/components/type-matchup-card.tsx`
- Modify: `frontend/app/page.tsx`
- Test: `frontend/tests/dashboard.test.tsx`

**Step 1: Write failing test**

Test the dashboard renders:
- video source selector
- player-side result panel
- opponent-side result panel
- linked info card section

**Step 2: Run test to verify failure**

Run: `cd frontend && npm test -- --runInBand dashboard.test.tsx`
Expected: FAIL.

**Step 3: Write minimal implementation**

Show a two-column or stacked layout with:
- selected video source
- recognition status
- player active Pokémon card
- opponent active Pokémon card
- matchup summary

**Step 4: Run test to verify pass**

Run: `cd frontend && npm test -- --runInBand dashboard.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend
git commit -m "feat: build recognition dashboard ui"
```

---

### Task 16: Add manual override UI

**Objective:** Make misrecognition recoverable in live streaming conditions.

**Files:**
- Create: `frontend/components/manual-override-form.tsx`
- Modify: `frontend/app/page.tsx`
- Test: `frontend/tests/manual-override-form.test.tsx`

**Step 1: Write failing test**

Test that the user can choose `player` or `opponent`, enter a Chinese Pokémon name, and submit override.

**Step 2: Run test to verify failure**

Run: `cd frontend && npm test -- --runInBand manual-override-form.test.tsx`
Expected: FAIL.

**Step 3: Write minimal implementation**

Provide a compact live-friendly override form with:
- side selector
- text input
- submit button
- latest override result status

**Step 4: Run test to verify pass**

Run: `cd frontend && npm test -- --runInBand manual-override-form.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend
git commit -m "feat: add manual override ui"
```

---

### Task 17: Add end-to-end local startup docs and scripts

**Objective:** Make the MVP runnable by a developer with clear startup steps.

**Files:**
- Create: `README.md`
- Create: `backend/Makefile`
- Create: `frontend/.env.local.example`
- Modify: `CLAUDE.md`
- Test: manual verification steps documented in README

**Step 1: Write failing test**

No automated unit test required; document manual acceptance checks before implementation.

**Step 2: Implement minimal documentation and scripts**

Include commands for:
- backend install
- frontend install
- backend dev server
- frontend dev server
- opening the second-window UI
- selecting a capture-card source
- checking current recognition
- using manual override

**Step 3: Run verification commands**

Run:
```bash
cd backend && pytest -q
cd ../frontend && npm test -- --runInBand
```
Expected: all pass.

**Step 4: Commit**

```bash
git add README.md backend frontend CLAUDE.md
git commit -m "docs: add local runbook for mvp"
```

---

### Task 18: Full integration verification

**Objective:** Confirm all MVP layers work together.

**Files:**
- Modify as needed based on failures
- Test: backend + frontend full suites

**Step 1: Run backend verification**

Run: `cd backend && pytest -q`
Expected: PASS.

**Step 2: Run frontend verification**

Run: `cd frontend && npm test -- --runInBand`
Expected: PASS.

**Step 3: Run startup smoke test**

Run backend and frontend locally, then manually verify:
1. Open UI in browser.
2. List video sources.
3. Start recognition session.
4. Confirm recognition state endpoint updates.
5. Manually override one side.
6. Confirm linked info and matchup display update.

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete mvp recognition query workflow"
```

---

## Acceptance Checklist

- [ ] Capture-card source enumeration exists
- [ ] Recognition session can start
- [ ] Current API returns both active names separately
- [ ] Chinese-first OCR adapter path is wired
- [ ] Manual override works per side
- [ ] Pokémon info lookup works from recognized names
- [ ] Type matchup lookup works
- [ ] Frontend dashboard works as a second-window tool
- [ ] Backend tests pass
- [ ] Frontend tests pass

---

## Verification Commands

```bash
cd backend && pytest -q
cd frontend && npm test -- --runInBand
```

Optional manual runtime:

```bash
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

---

## Risks To Watch During Execution

1. OpenCV device indexing differs by OS and hardware.
2. Capture-card labels may be inconsistent.
3. Chinese OCR may misread stylized UI text from the game.
4. Name normalization must tolerate OCR noise.
5. Real-time polling frequency must not overload CPU during streaming.

---

## Notes For Execution Agent

- Keep OCR provider behind an adapter. Do not hard-code one library everywhere.
- Build manual override early enough that live use is always recoverable.
- Do not attempt full battle parsing in this MVP.
- Prefer deterministic tests with mocked OCR and mocked frame inputs.
- If hardware access is unavailable in CI, keep source enumeration and capture tests mockable.

---

**Plan complete. Ready to execute using subagent-driven-development — dispatch a fresh subagent per task with spec compliance review first and code quality review second.**
