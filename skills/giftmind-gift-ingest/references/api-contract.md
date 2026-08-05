# GiftMind Agent ingestion API

## Request

`POST /api/agent/gifts/ingest` uses the existing authenticated session cookie. The bundled script first calls `POST /api/session/login` with `GIFTMIND_TEAM_PASSCODE`.

Multipart fields:

- `description`: up to 8,000 characters of factual observations and collector context.
- `gift_type_code`: `auto`, `product`, or `activity`.
- `lifecycle_status`: `draft` by default; also accepts `active` or `inactive`.
- `analysis_mode`: `local` or `cloud`. The bundled client defaults to `local`; the raw API keeps `cloud` as a backward-compatible default.
- `source_urls_json`: JSON string array, up to 20 public HTTP/HTTPS URLs.
- `known_fields_json`: JSON object using GiftMind camelCase fields. Explicit values override AI suggestions.
- `images`: repeatable JPG, PNG, or WebP file; at most 4 files and 8 MB each.

Useful `known_fields_json` fields include:

```json
{
  "canonicalName": "礼物名称",
  "priceMin": 69,
  "priceMax": 99,
  "collectorNotes": "采集备注",
  "productDetails": {
    "colors": ["金色"],
    "materials": ["黄铜"],
    "variantNotes": "可选圆形和方形"
  }
}
```

The bundled client also maps repeatable `--material`, `--color`, and `--size` values into `productDetails`, and accepts `--generic-product-name`, `--variant-notes`, `--source-notes`, and `--specifications-json`.

For verified Taobao/Tmall observations, use `--taobao-shop-name`, `--taobao-item-id`, repeatable `--taobao-sku 'dimension=value'`, `--taobao-price`, and `--taobao-observed-at`. These flags create:

```json
{
  "priceMin": 158,
  "priceMax": 158,
  "sourceNotes": "淘宝实证：店铺=示例旗舰店；itemId=123；SKU=颜色=蓝色；详情页价格=CNY 158；采集时间=2026-08-05T17:30:00+08:00",
  "productDetails": {
    "specifications": {
      "taobaoEvidence": {
        "platform": "taobao",
        "shopName": "示例旗舰店",
        "itemId": "123",
        "selectedSku": {"颜色": "蓝色"},
        "observedPriceCny": 158,
        "observedAt": "2026-08-05T17:30:00+08:00",
        "priceEvidence": "detail-sku"
      }
    }
  }
}
```

Only use `priceEvidence: detail-sku` after the exact SKU has been selected and the refreshed detail-page price has been observed. Search-card and `￥xx 起` prices must not populate `priceMin` or `priceMax`.

For activities, use `activityDetails` fields such as `activityMode`, `serviceRegions`, `durationMinutesMin`, `durationMinutesMax`, `participantsMin`, `participantsMax`, `pricingUnit`, and `bookingRequired`.

## Response

Success is HTTP 201 with:

- `gift`: the persisted typed database record.
- `images`: stored image records; the first image is the cover.
- `analysis.source`: `deepseek` or deterministic `rule` fallback.
- `analysis.mode`: requested `local` or `cloud` mode.
- `analysis.source`: `local-agent` in local mode, otherwise `deepseek` or deterministic `rule` fallback.
- `analysis.confidence`: aggregate suggestion confidence.
- `analysis.questions`: facts still worth human confirmation.
- `analysis.sourceRefs`: compact extraction status for links and images.

Exact duplicates return HTTP 409 with `detail.code = DUPLICATE_GIFT`. Insufficient or invalid data returns HTTP 422 with validation errors and, when available, follow-up questions.

## Local mode

With `analysis_mode=local`, the server does not fetch source pages, understand images, or call DeepSeek. It validates and stores `known_fields_json`, source URLs, and uploaded images. The local Agent must prepare the structured fields before ingestion. Uploaded images are stored without server-side OCR or vision analysis.

The bundled client requires server metadata version 1.1.0 or newer before sending a local-mode ingestion request. This prevents an older server from ignoring the new form field and silently running cloud analysis.

Use `analysis_mode=cloud` only when the user explicitly requests server-side enrichment.

## Counts

`GET /api/agent/gifts/counts` returns current non-deleted records as `productCount`, `activityCount`, `totalCount`, and `byStatus` (`draft`, `active`, `inactive`). It uses the same authenticated session.
