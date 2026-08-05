---
name: giftmind-gift-ingest
description: Analyze gift product or activity images, links, screenshots, names, prices, colors, and collector notes, then create a structured draft in the GiftMind database through its Agent ingestion API. Use when the user sends gift materials and asks to summarize, classify, enrich, record, add, import, or push them into GiftMind.
---

# GiftMind Gift Ingest

Turn mixed gift evidence into one database draft by using the bundled deterministic client.

## Workflow

1. Inspect every supplied image and extract only visible facts: product/activity identity, visible text, color, material, dimensions, variant, packaging, and displayed price. Do not infer a merchant, exact material, or price that is not supported.
2. Combine those observations with user text and links into a concise Chinese `description`. Preserve the user's explicit values in `knownFields`; explicit values override AI suggestions.
3. Keep `giftType` as `auto` unless the user explicitly identifies it. An activity means the giver and recipient participate together; a single-person voucher or service is a product.
4. Run `scripts/ingest_gift.py`. Read `references/api-contract.md` only when adding advanced fields or diagnosing a response.
5. Report the created gift ID, type, draft/active status, analysis source, confidence, stored images, and remaining questions.

## Command

Set configuration in environment variables; never place the passcode in a command or committed file.

```powershell
$env:GIFTMIND_API_URL='http://127.0.0.1:8000'
$env:GIFTMIND_TEAM_PASSCODE='the-team-passcode'
python scripts/ingest_gift.py --description '南京主题金属书签，标价 69 元' --image 'C:\path\gift.jpg' --name '南京主题金属书签' --color '金色'
```

Add repeatable `--image`, `--source-url`, and `--color` arguments as needed. Use `--known-json` for any schema fields not exposed as flags. Default to `--status draft`; use `active` only when the user explicitly asks to publish immediately.

Run `python scripts/ingest_gift.py --counts` to return the current product, activity, total, and lifecycle-status counts without creating a record.

## Result handling

- On `201`, report the returned database record; do not claim values absent from the response.
- On `409 DUPLICATE_GIFT`, stop and show the existing match. Do not rename the same gift to bypass duplicate protection.
- On `422 INCOMPLETE_GIFT`, ask only for the missing facts returned in `questions` or `errors`, then retry once with those facts.
- If `analysis.source` is `rule`, state that DeepSeek was unavailable or not configured; the draft was still built from deterministic extraction.
- Keep image observations factual. Treat AI-generated audience, occasion, and gift-reason fields as suggestions stored on a draft, not verified facts.

## Required boundaries

- Never send `.env`, API keys, cookies, or the team passcode as gift content.
- Never write directly to SQLite or bypass the ingestion endpoint.
- Never mark a record verified. Human review owns verification.
- Do not upload more than four images; each must be JPG, PNG, or WebP and at most 8 MB.
