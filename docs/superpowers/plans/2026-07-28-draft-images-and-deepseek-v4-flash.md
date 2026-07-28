# Draft Images and DeepSeek V4 Flash Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let collectors attach images before a gift exists, upload them safely after the first save, and make DeepSeek V4 Flash the single configured AI model.

**Architecture:** `ImageManager.vue` owns local pending files and server image rendering while `GiftWorkbenchView.vue` orchestrates create-then-upload-then-reset. The backend exposes one `DEEPSEEK_MODEL` constant used by status responses and inference requests.

**Tech Stack:** Vue 3, TypeScript, Pinia, Vitest, FastAPI, pytest, httpx.

## Global Constraints

- Supported images are JPEG, PNG, and WebP, with an 8MB maximum per file.
- Images selected before first save remain client-side and are not persisted across page refresh.
- AI suggestions never write gift records directly.
- DeepSeek API keys remain in `.env` and are never returned to the browser.
- Do not add accounts, roles, CSRF, rate limiting, or temporary-upload database tables.

---

### Task 1: Centralize the DeepSeek model

**Files:**
- Modify: `backend/app/api/routes/tools.py`
- Modify: `tests/api/test_tools.py`
- Modify: `frontend/src/views/__tests__/ToolsView.test.ts`

**Interfaces:**
- Produces: `DEEPSEEK_MODEL: str = "deepseek-v4-flash"`
- Produces: settings response `{ configured: boolean, model: "deepseek-v4-flash" }`

- [ ] **Step 1: Write failing backend expectations**

Change settings assertions to `deepseek-v4-flash` and capture the fake HTTP client's JSON body:

```python
assert response.json()["model"] == "deepseek-v4-flash"
assert captured_request["json"]["model"] == "deepseek-v4-flash"
```

- [ ] **Step 2: Run the focused tests**

Run: `python -m pytest tests/api/test_tools.py -q`

Expected: FAIL because the current model is `deepseek-chat`.

- [ ] **Step 3: Add and use the model constant**

```python
DEEPSEEK_MODEL = "deepseek-v4-flash"
```

Use it in `deepseek_status`, `save_deepseek_key`, and the `/chat/completions` request payload.

- [ ] **Step 4: Update frontend fixture expectations**

Replace test fixtures and visible status expectations with `deepseek-v4-flash`.

- [ ] **Step 5: Run focused tests**

Run: `python -m pytest tests/api/test_tools.py -q`

Run: `npm run test -- --run src/views/__tests__/ToolsView.test.ts`

Expected: both PASS.

### Task 2: Add a pending-image state machine

**Files:**
- Modify: `frontend/src/components/gifts/ImageManager.vue`
- Create: `frontend/src/components/gifts/__tests__/ImageManager.test.ts`

**Interfaces:**
- Consumes: optional prop `giftId?: string`
- Produces: exposed `uploadPending(giftId: string): Promise<void>`
- Produces: exposed `clearPending(): void`
- Produces: exposed `hasPending(): boolean`

- [ ] **Step 1: Write failing component tests**

Cover these cases:

```ts
expect(wrapper.get('[data-image-input]').exists()).toBe(true)
expect(wrapper.findAll('[data-pending-image]')).toHaveLength(2)
expect(wrapper.get('[data-image-error]').text()).toContain("8MB")
```

Mock `URL.createObjectURL`, `URL.revokeObjectURL`, and `fetch`. Assert `uploadPending("gift-1")` posts each accepted file to `/api/gifts/gift-1/images`, removes successful items, and retains failed items.

- [ ] **Step 2: Run the focused test**

Run: `npm run test -- --run src/components/gifts/__tests__/ImageManager.test.ts`

Expected: FAIL because `giftId` is required and no pending queue exists.

- [ ] **Step 3: Implement pending image selection**

Add a `PendingImage` interface containing `id`, `file`, `previewUrl`, `status`, and `error`. Accept multiple files, validate MIME type and size, render previews, and allow removal.

- [ ] **Step 4: Implement upload and cleanup**

Expose methods with `defineExpose`. Upload sequentially so each item has an individual visible result. Remove and revoke successful entries; retain failed entries with error text.

- [ ] **Step 5: Run the focused test**

Run: `npm run test -- --run src/components/gifts/__tests__/ImageManager.test.ts`

Expected: PASS.

### Task 3: Orchestrate save before image upload

**Files:**
- Modify: `frontend/src/views/GiftWorkbenchView.vue`
- Modify: `frontend/src/components/gifts/__tests__/GiftWorkbench.test.ts`

**Interfaces:**
- Consumes: `ImageManager.uploadPending(saved.id)`
- Consumes: `store.saveDraft(): Promise<GiftRead>`
- Produces: create → image upload → optional reset ordering

- [ ] **Step 1: Write failing workbench tests**

Add tests asserting:

```ts
expect(wrapper.get('[data-image-input]').exists()).toBe(true)
expect(callOrder).toEqual(["create-gift", "upload-image"])
expect(nameInput.value).toBe("黄铜书签") // retained after failed image upload
expect(pendingImages).toHaveLength(1)
```

Also verify “保存并新建下一条” clears the name and pending images only after successful upload.

- [ ] **Step 2: Run the focused test**

Run: `npm run test -- --run src/components/gifts/__tests__/GiftWorkbench.test.ts`

Expected: FAIL because the manager is hidden and reset happens inside the store before upload.

- [ ] **Step 3: Render the manager for every draft**

Remove the conditional rendering and pass `store.giftId ?? undefined`.

- [ ] **Step 4: Reorder saving**

Use one page-level save flow:

```ts
const saved = await store.saveDraft()
await imageManager.value?.uploadPending(saved.id)
if (kind === "next") store.startNew()
```

Only clear local draft and duplicate feedback after the image step succeeds.

- [ ] **Step 5: Run focused frontend tests**

Run: `npm run test -- --run src/components/gifts/__tests__/GiftWorkbench.test.ts src/components/gifts/__tests__/ImageManager.test.ts`

Expected: PASS.

### Task 4: Full verification and browser check

**Files:**
- Modify: `docs/superpowers/plans/2026-07-28-draft-images-and-deepseek-v4-flash.md` (mark completed steps)

**Interfaces:**
- Produces: verified local preview and repository commit

- [ ] **Step 1: Run backend tests**

Run: `python -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 2: Run frontend validation**

Run: `npm run test`

Run: `npm run typecheck`

Run: `npm run build`

Expected: all commands PASS.

- [ ] **Step 3: Verify in the browser**

Start the FastAPI server and Vite dev server, log in with the configured preview passcode, open `/gifts/new`, select a valid image, confirm its preview, save a named gift, and confirm the image is visible after the server reload.

- [ ] **Step 4: Verify the model status**

Open `/tools` and confirm the DeepSeek status displays `deepseek-v4-flash`.

- [ ] **Step 5: Commit**

```bash
git add backend tests frontend docs
git commit -m "feat: add draft images and DeepSeek V4 Flash"
```

## Completion Record

- [x] DeepSeek status, key-save response, and inference requests use `deepseek-v4-flash`.
- [x] New gifts expose a multi-image picker before a gift ID exists.
- [x] Pending images are validated, previewed, removable, and uploaded after gift creation.
- [x] Failed uploads retain the form and failed image with retry feedback.
- [x] “保存并新建下一条” resets only after image upload succeeds.
- [x] Backend tests: 45 passed.
- [x] Frontend tests: 30 passed.
- [x] Frontend typecheck and production build passed.
- [x] Browser verification confirmed pending preview, post-save upload, and DeepSeek V4 Flash status.
