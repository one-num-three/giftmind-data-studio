# Guided Gift Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a concise, desktop-first guided workbench for creating and editing one product or activity gift.

**Architecture:** A Pinia workbench store owns one discriminated UI draft and maps it to the existing camelCase backend contract at a single API boundary. Focused form components edit common and type-specific state, while the view composes them into responsive progress, form, and quality columns. A composable persists a local-only draft and another prevents accidental route or tab exit.

**Tech Stack:** Vue 3, TypeScript, Pinia, Vue Router, Vitest, Vue Test Utils, existing `apiRequest` client.

## Global Constraints

- Product and activity forms remain clearly separate.
- Keep the existing lightweight passcode/cookie session model; add no accounts, roles, CSRF, rate limits, token persistence, or API-key UI.
- Do not add later list, import, AI, or image features.
- Save local drafts after a 500 ms debounce under a schema-versioned `new` or gift UUID key; never auto-submit them.

---

### Task 1: Establish the failing workbench behaviors

**Files:**
- Create: `frontend/src/components/gifts/__tests__/GiftWorkbench.test.ts`

- [x] **Step 1: Write failing conditional-form tests**

```ts
it('shows only product fields after product confirmation', async () => {
  const wrapper = mountWorkbench()
  await wrapper.get('[data-type="product"]').trigger('click')
  expect(wrapper.find('[data-section="product"]').exists()).toBe(true)
  expect(wrapper.find('[data-section="activity"]').exists()).toBe(false)
})
```

- [x] **Step 2: Run the targeted test**

Run: `npm run test -- GiftWorkbench`
Expected: the missing workbench component import fails.

### Task 2: Add typed draft, API serialization, and local-draft primitives

**Files:**
- Create: `frontend/src/api/gifts.ts`
- Create: `frontend/src/stores/workbench.ts`
- Create: `frontend/src/composables/useDraft.ts`
- Create: `frontend/src/composables/useUnsavedChanges.ts`

- [x] **Step 1: Implement the discriminated `GiftDraft` and serializer**

```ts
export type GiftDraft = ProductGiftDraft | ActivityGiftDraft
export function toGiftPayload(draft: GiftDraft): GiftPayload
```

- [x] **Step 2: Implement a store with `saveDraft`, `saveAndContinue`, and `saveAndCreateNext`**

```ts
async saveDraft(): Promise<GiftRead>
async saveAndContinue(): Promise<GiftRead>
async saveAndCreateNext(): Promise<void>
```

- [x] **Step 3: Add the 500 ms draft persistence and route/tab navigation guard**

```ts
export function useDraft(key: Ref<string>, draft: Ref<GiftDraft>)
export function useUnsavedChanges(dirty: Ref<boolean>)
```

### Task 3: Build the focused editor components

**Files:**
- Create: `frontend/src/components/gifts/GiftTypeSelector.vue`
- Create: `frontend/src/components/gifts/WorkbenchProgress.vue`
- Create: `frontend/src/components/gifts/CommonFieldsSection.vue`
- Create: `frontend/src/components/gifts/ProductFieldsSection.vue`
- Create: `frontend/src/components/gifts/ActivityFieldsSection.vue`
- Create: `frontend/src/components/gifts/OfferEditor.vue`
- Create: `frontend/src/components/gifts/BundleEditor.vue`
- Create: `frontend/src/components/gifts/QualityPanel.vue`

- [x] **Step 1: Render common, matching, channel, bundle, and quality fields**

```vue
<CommonFieldsSection v-model="draft" />
<OfferEditor v-model="draft" />
<BundleEditor v-model="draft" />
```

- [x] **Step 2: Render exactly one of the type-specific sections and require confirmation before dropping type-specific state**

```vue
<ProductFieldsSection v-if="draft.giftTypeCode === 'product'" v-model="draft.productDetails" />
<ActivityFieldsSection v-else v-model="draft.activityDetails" />
```

### Task 4: Compose the responsive workbench and register it

**Files:**
- Create: `frontend/src/views/GiftWorkbenchView.vue`
- Modify: `frontend/src/router/index.ts`

- [x] **Step 1: Compose the three-column desktop layout and one-column narrow layout**

```vue
<WorkbenchProgress :sections="sections" />
<form @submit.prevent="saveAndContinue">...</form>
<QualityPanel :draft="draft" />
```

- [x] **Step 2: Register `/gifts/new` and `/gifts/:giftId` under the authenticated shell**

```ts
{ path: 'gifts/new', name: 'gift-create', component: GiftWorkbenchView }
{ path: 'gifts/:giftId', name: 'gift-edit', component: GiftWorkbenchView }
```

### Task 5: Finish the test cycle and verify production build

**Files:**
- Modify: `frontend/src/components/gifts/__tests__/GiftWorkbench.test.ts`

- [x] **Step 1: Add restore/discard, save action, and type-switch confirmation coverage**

```ts
expect(wrapper.text()).toContain('商品专属信息不会用于活动记录')
```

- [x] **Step 2: Run verification commands**

Run: `npm run test -- GiftWorkbench`, `npm run typecheck`, and `npm run build` from `frontend`.
Expected: each exits 0.

- [x] **Step 3: Commit the implementation**

```powershell
git add frontend/src docs/superpowers/plans
git commit -m "feat: add guided product and activity workbench"
```
