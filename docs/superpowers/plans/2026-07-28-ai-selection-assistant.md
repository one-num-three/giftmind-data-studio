# AI Selection Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a persistent, per-gift AI chat assistant that turns text and public links into reviewable field patches without directly saving gift records.

**Architecture:** FastAPI persists threads, messages, and suggestion runs in three new tables. A focused extraction service fetches bounded public HTML, and a suggestion service converts DeepSeek or fallback output into a strict field whitelist. Vue renders a floating chat drawer and sends accepted patches to the workbench, which owns field mutation, undo, and highlights.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async, Alembic, httpx, Vue 3, Pinia, TypeScript, Vitest.

## Global Constraints

- AI never calls the gift create or update API.
- Every new gift uses a distinct `draftId`; existing gifts use a stable gift-derived draft key.
- DeepSeek model is `deepseek-v4-flash`.
- Link extraction accepts at most 3 public HTTP/HTTPS URLs, 1MB each, with a 10-second timeout.
- Unknown patch paths are discarded.
- High confidence means `confidence >= 0.8`.
- Image OCR and vision are not simulated in this phase; attachment arrays remain empty.

---

### Task 1: Persist AI threads, messages, and suggestion runs

**Files:**
- Create: `backend/app/models/assistant.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/0002_ai_assistant_threads.py`
- Create: `tests/models/test_ai_assistant_models.py`

**Interfaces:**
- Produces: `AIThread`, `AIMessage`, `AISuggestionRun`
- Produces: unique `AIThread.draft_id`
- Produces: nullable `AIThread.gift_id`

- [ ] **Step 1: Write the failing model test**

```python
async def test_threads_are_isolated_by_draft_id(db_session):
    first = AIThread(draft_id="draft-a")
    second = AIThread(draft_id="draft-b")
    db_session.add_all([first, second])
    await db_session.commit()
    assert first.id != second.id
    assert first.draft_id == "draft-a"
    assert second.draft_id == "draft-b"
```

Also assert that messages and suggestion runs preserve their own thread IDs.

- [ ] **Step 2: Run the test and confirm red**

Run: `python -m pytest tests/models/test_ai_assistant_models.py -q`

Expected: import failure because the assistant models do not exist.

- [ ] **Step 3: Implement models and migration**

Use UUID string primary keys and existing timestamp mixins. Store attachments, source references, patches, applied fields, and ignored fields as JSON. Add cascading foreign keys from messages/runs to threads and set-null behavior from threads to gifts.

- [ ] **Step 4: Run model and migration tests**

Run: `python -m pytest tests/models/test_ai_assistant_models.py tests/migrations -q`

Expected: PASS.

### Task 2: Extract public link context and normalize field patches

**Files:**
- Create: `backend/app/services/source_extraction.py`
- Create: `backend/app/services/assistant_suggestions.py`
- Create: `tests/services/test_source_extraction.py`
- Create: `tests/services/test_assistant_suggestions.py`

**Interfaces:**
- Produces: `extract_urls(text: str) -> list[str]`
- Produces: `extract_public_page(url: str, client: httpx.AsyncClient) -> SourceReference`
- Produces: `suggestion_to_patches(suggestion: dict, source_refs: list[dict]) -> list[dict]`
- Produces: `build_assistant_reply(...) -> AssistantResult`

- [ ] **Step 1: Write failing URL extraction tests**

```python
def test_extract_urls_deduplicates_and_limits_to_three():
    text = " ".join(["https://a.test/x", "https://a.test/x", "https://b.test", "https://c.test", "https://d.test"])
    assert extract_urls(text) == ["https://a.test/x", "https://b.test", "https://c.test"]
```

Add tests rejecting `file:`, localhost, loopback, and private IP destinations.

- [ ] **Step 2: Write failing HTML extraction tests**

Use `httpx.MockTransport` with a page containing `<title>`, meta description, visible price text, and JSON-LD Product data. Assert bounded normalized output and a stable source reference.

- [ ] **Step 3: Implement bounded extraction**

Use `urllib.parse`, `ipaddress`, `socket.getaddrinfo`, and `html.parser.HTMLParser`. Strip scripts/styles, keep title/description/body/JSON-LD, and return a failure reference instead of raising for ordinary page errors.

- [ ] **Step 4: Write failing patch normalization tests**

```python
def test_patch_normalizer_drops_unknown_paths_and_clamps_confidence():
    raw = {"priceMin": 39, "unknownSecret": "x", "confidence": 4}
    patches = suggestion_to_patches(raw, [{"label": "用户描述"}])
    assert [item["path"] for item in patches] == ["priceMin"]
    assert patches[0]["confidence"] == 1
```

Cover product and activity nested paths, arrays, booleans, and null omission.

- [ ] **Step 5: Implement suggestion service**

Reuse the current DeepSeek prompt/normalization behavior through focused functions, include the last 12 messages and extracted source context, and return rule-based low-confidence patches when no key or valid model response exists.

- [ ] **Step 6: Run focused service tests**

Run: `python -m pytest tests/services/test_source_extraction.py tests/services/test_assistant_suggestions.py -q`

Expected: PASS.

### Task 3: Expose thread, message, review, and bind APIs

**Files:**
- Create: `backend/app/api/routes/assistant.py`
- Modify: `backend/app/api/router.py`
- Create: `tests/api/test_assistant.py`

**Interfaces:**
- Produces: `POST /api/ai/threads`
- Produces: `GET /api/ai/threads/{thread_id}`
- Produces: `POST /api/ai/threads/{thread_id}/messages`
- Produces: `PATCH /api/ai/suggestion-runs/{run_id}`
- Produces: `PATCH /api/ai/threads/{thread_id}/bind`

- [ ] **Step 1: Write failing thread isolation tests**

Create two draft IDs, send different messages, reload both threads, and assert no message crosses thread boundaries. Repeat thread creation with the same draft ID and assert idempotent reuse.

- [ ] **Step 2: Write failing message and fallback tests**

Submit text plus a mocked public link. Assert a user message, assistant message, source reference, and whitelisted suggestion run are persisted. With no key, assert the fallback source and low confidence remain usable.

- [ ] **Step 3: Write failing review and bind tests**

Patch applied/ignored fields and reload the thread. Create a gift, bind the thread, and assert its `giftId`. Bind an unknown gift and expect 404.

- [ ] **Step 4: Implement API schemas and handlers**

Validate UUIDs through route parameters, require the existing team session, cap content at 8,000 characters, and keep message transactions consistent: user message persists even if model inference degrades.

- [ ] **Step 5: Run assistant API tests**

Run: `python -m pytest tests/api/test_assistant.py -q`

Expected: PASS.

### Task 4: Add draft identity and assistant client state

**Files:**
- Modify: `frontend/src/stores/workbench.ts`
- Modify: `frontend/src/composables/useDraft.ts`
- Create: `frontend/src/api/assistant.ts`
- Create: `frontend/src/stores/__tests__/assistant-draft.test.ts`

**Interfaces:**
- Produces: `WorkbenchState.draftId: string`
- Produces: `createOrRestoreThread`, `loadThread`, `sendThreadMessage`, `reviewSuggestionRun`, `bindThreadGift`
- Preserves: draft ID through save
- Rotates: draft ID only on `startNew()`

- [ ] **Step 1: Write failing draft lifecycle tests**

```ts
const first = store.draftId
await store.saveDraft()
expect(store.draftId).toBe(first)
store.startNew()
expect(store.draftId).not.toBe(first)
```

Assert restored local drafts include their original draft ID.

- [ ] **Step 2: Implement draft ID lifecycle**

Generate IDs with `crypto.randomUUID()`, include `draftId` in local draft storage version 2, migrate version 1 drafts by assigning a new ID, and use `gift-${giftId}` when loading an existing gift without stored assistant identity.

- [ ] **Step 3: Add typed assistant API client**

Define exact interfaces for `AIThreadRead`, `AIMessageRead`, `AISuggestionRunRead`, and `FieldSuggestion`. Use the existing `apiRequest` helper.

- [ ] **Step 4: Run focused frontend state tests**

Run: `npm run test -- --run src/stores/__tests__/assistant-draft.test.ts`

Expected: PASS.

### Task 5: Build the floating assistant and field-review workflow

**Files:**
- Create: `frontend/src/components/assistant/AISelectionAssistant.vue`
- Create: `frontend/src/components/assistant/__tests__/AISelectionAssistant.test.ts`
- Create: `frontend/src/composables/useAISuggestionPatch.ts`
- Create: `frontend/src/composables/__tests__/useAISuggestionPatch.test.ts`
- Modify: `frontend/src/views/GiftWorkbenchView.vue`

**Interfaces:**
- Consumes: `draftId`, `giftId`, `giftTypeCode`, `currentValues`
- Emits: `apply-field`, `apply-many`, `undo-field`
- Produces: collapsed/expanded drawer, messages, source labels, confidence, apply/ignore/undo
- Produces: `appliedHighlights: Set<string>`

- [ ] **Step 1: Write failing patch application tests**

```ts
const state = createPatchState(draft)
state.apply({ path: "priceMin", value: 39, confidence: 0.91 })
expect(draft.value.priceMin).toBe(39)
state.undo("priceMin")
expect(draft.value.priceMin).toBe(null)
```

Cover nested product/activity fields, apply-all, confidence filtering, highlight creation, and highlight removal after manual mutation.

- [ ] **Step 2: Implement the patch composable**

Whitelist client paths to match the backend, snapshot the previous value on first apply, clone arrays, and compare serialized values in a deep watcher to remove highlights after human edits.

- [ ] **Step 3: Write failing assistant component tests**

Assert the drawer starts collapsed, expands uniquely, sends text, renders messages and sources, applies one field, ignores one field, applies confidence `>= 0.8`, and never calls `/api/gifts`.

- [ ] **Step 4: Implement the assistant drawer**

Create or restore the thread on first expansion, show a sending state, render field cards, record review results, and keep errors inside the drawer. Use a 390px desktop panel and full-width mobile bottom sheet.

- [ ] **Step 5: Integrate with the workbench**

Pass `store.draftId`, `store.giftId`, and the current draft. Bind the thread after a successful save. Rotate to a fresh assistant instance after “保存并新建下一条”. Apply type suggestions through the existing type-switch rules and show highlights using stable `data-field` selectors.

- [ ] **Step 6: Run focused UI tests**

Run: `npm run test -- --run src/components/assistant/__tests__/AISelectionAssistant.test.ts src/composables/__tests__/useAISuggestionPatch.test.ts src/components/gifts/__tests__/GiftWorkbench.test.ts`

Expected: PASS.

### Task 6: Full verification and delivery

**Files:**
- Modify: `docs/superpowers/plans/2026-07-28-ai-selection-assistant.md`

**Interfaces:**
- Produces: verified local preview and pushed GitHub commit

- [ ] **Step 1: Run backend verification**

Run: `python -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 2: Run frontend verification**

Run: `npm run test`

Run: `npm run typecheck`

Run: `npm run build`

Expected: all commands PASS.

- [ ] **Step 3: Run browser workflow**

Create a new gift, expand the assistant, send a text/link message, apply a high-confidence field, verify form highlight, edit the field manually, verify highlight clears, save the gift, and verify the thread remains bound and reloadable.

- [ ] **Step 4: Commit and push**

```bash
git add backend frontend tests docs
git commit -m "feat: add persistent AI selection assistant"
git push origin main
```

