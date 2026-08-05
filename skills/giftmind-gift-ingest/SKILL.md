---
name: giftmind-gift-ingest
description: Locally analyze and enrich gift products or activities from images, links, screenshots, names, prices, variants, colors, and collector notes, then create a structured GiftMind draft through the Agent ingestion API without relying on cloud AI by default. Use when the user asks to summarize, research, classify, complete, record, import, or push a gift into GiftMind, especially when a Taobao/Tmall item needs accurate details, selected-SKU information, or a verified detail-page price via taobao-native.
---

# GiftMind Gift Ingest

Turn mixed gift evidence into one locally analyzed database draft with the bundled deterministic client. Treat the server as validation and storage by default, not as the primary analyst.

## Workflow

1. Inspect every supplied image. Record only visible identity, text, color, material, dimensions, variant, packaging, and displayed price.
2. Build an evidence ledger before writing fields. Apply this priority:
   1. explicit user values;
   2. exact Taobao/Tmall detail-page and selected-SKU observations;
   3. visible image facts;
   4. other source-page text;
   5. local Agent judgments marked as suggestions;
   6. cloud AI suggestions, only when explicitly enabled.
3. When evidence includes a Taobao/Tmall URL, item ID, product name to research, or a request for an accurate price, use `$taobao-native` and follow [references/taobao-enrichment.md](references/taobao-enrichment.md) before ingestion.
4. Perform the substantive analysis locally. Follow [references/local-analysis.md](references/local-analysis.md) and prepare a complete UTF-8 `knownFields` JSON object before calling the API.
5. Combine verified observations, user context, and links into a concise Chinese `description`. Put facts and clearly labeled local suggestions in `knownFields`; never leave routine semantic analysis to cloud DeepSeek.
6. Keep `giftType` as `auto` unless the user explicitly identifies it. Treat a shared giver-recipient experience as an activity; treat a single-person voucher or service as a product.
7. Run `scripts/ingest_gift.py` in its default `local` analysis mode. Read [references/api-contract.md](references/api-contract.md) for advanced fields or response diagnosis.
8. Report the gift ID, type, lifecycle status, analysis source, confidence, stored images, evidence limitations, and remaining questions.

## Local-first rule

- Inspect images and source evidence with local Agent tools before ingestion.
- Locally generate the canonical name, concise description, type, recipients, occasions, interests, tags, gift reasons, suitable and unsuitable scenarios, purchase advice, ritual idea, pairing idea, risks, and typed product/activity details.
- Separate observed facts from local recommendations. Put provenance in `sourceNotes` and uncertainty in `collectorNotes` or `variantNotes`.
- Pass the completed object with `--known-json`. The default `--analysis-mode local` makes the server skip link extraction, image understanding, and DeepSeek.
- Let the client preflight `/api/agent/skill`. It refuses local ingestion on servers older than 1.1.0 instead of silently falling back to cloud analysis.
- Use `--analysis-mode cloud` only when the user explicitly requests server-side AI analysis. Never use it merely because local analysis takes more work.

## Taobao enrichment gate

- Treat search results as discovery evidence only. Never store a search-card price or `￥xx 起` as the gift price.
- Resolve the intended SKU from the user's words. If several materially different SKUs remain plausible, show the options and ask; do not choose the cheapest or default SKU silently.
- Obtain a real price only after opening the detail page, scanning the full DOM, clicking the exact SKU by `index`, waiting at least 3 seconds, and rescanning the refreshed price.
- Capture, when available: canonical title, shop name, item ID, trusted URL, selected SKU labels and values, exact CNY price, observation time, main/SKU images, visible materials, colors, sizes, specifications, shipping notes, and return or warranty statements.
- Record unavailable facts as missing. Do not infer merchant identity, material, capacity, compatibility, stock, shipping promise, or warranty.

## Command

Set configuration in environment variables. Never submit the passcode as gift content or a CLI argument.

```powershell
$env:GIFTMIND_API_URL='https://giftmind.example.com'
$env:GIFTMIND_TEAM_PASSCODE='configured-outside-the-command'
python scripts/ingest_gift.py --description '南京主题金属书签' --image 'C:\path\gift.jpg' --name '南京主题金属书签' --color '金色'
```

For a Taobao-selected SKU, pass verified evidence explicitly:

```powershell
python scripts/ingest_gift.py `
  --description '蓝色陶瓷杯礼盒，详情页已核对指定规格' `
  --known-json 'C:\workspace\gift-known-fields.json' `
  --source-url 'https://item.taobao.com/item.htm?id=123' `
  --name '自由飞鸟杯子礼盒' `
  --generic-product-name '杯子礼盒' `
  --material '陶瓷' --color '蓝色' `
  --taobao-item-id '123' --taobao-shop-name '示例旗舰店' `
  --taobao-sku '颜色=蓝色' --taobao-sku '包装=礼盒装' `
  --taobao-price 158 --taobao-observed-at '2026-08-05T17:30:00+08:00'
```

Use repeatable `--image`, `--source-url`, `--color`, `--material`, `--size`, and `--taobao-sku` arguments. Use `--specifications-json` for structured specifications and `--known-json` for any remaining schema fields. Default to `--status draft`; use `active` only when the user explicitly asks to publish immediately.

The client defaults to `--analysis-mode local`. In this mode, a description or image alone is not a substitute for local structured analysis; provide at least the locally determined `canonicalName` and type-specific details through flags or `--known-json`.

Local mode requires GiftMind server 1.1.0 or newer. Deploy the matching backend before using an older cloud instance. The client aborts safely when the server is too old.

Run `python scripts/ingest_gift.py --counts` to return product, activity, total, and lifecycle counts without creating a record.

## Evidence handling

- Store exact Taobao evidence under `productDetails.specifications.taobaoEvidence`; the client builds this object from `--taobao-*` flags.
- Set `priceMin` and `priceMax` to the same value only for one exact observed SKU price. Use a range only when both endpoints are supported by verified target-SKU observations.
- Put provenance and limitations in `sourceNotes` or `collectorNotes`, including the selected SKU and observation time.
- Treat AI-generated audience, occasion, gift-reason, material, and compatibility fields as draft suggestions unless another source verifies them.
- Prefer local Agent suggestions over cloud suggestions and identify them as judgments, not observed product facts.
- Never mark a record verified. Human review owns verification even when the price was observed accurately.

## Result handling

- On `201`, report only values present in the returned record.
- On `409 DUPLICATE_GIFT`, stop and show the existing match. Never rename the same gift to bypass duplicate protection.
- On `422 INCOMPLETE_GIFT`, ask only for facts returned in `questions` or `errors`, then retry once.
- If `analysis.source` is `rule`, state that DeepSeek was unavailable or not configured and deterministic extraction still created the draft.
- If `analysis.source` is `local-agent`, state that the record was built from the locally supplied structured analysis and the server did not call DeepSeek.
- If Taobao is unavailable, continue with non-Taobao evidence only when useful, leave price unset, and name the failed evidence step.

## Required boundaries

- Never send `.env`, API keys, cookies, session data, or the team passcode as gift content.
- Never write directly to SQLite or bypass the ingestion endpoint.
- Never add to cart, buy, message a merchant, rate a product, or modify a Taobao account while enriching a GiftMind record.
- Never mark a record verified.
- Upload at most four JPG, PNG, or WebP images, each at most 8 MB.
