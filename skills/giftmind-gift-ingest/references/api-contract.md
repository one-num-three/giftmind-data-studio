# GiftMind Agent ingestion API

## Request

`POST /api/agent/gifts/ingest` uses the existing authenticated session cookie. The bundled script first calls `POST /api/session/login` with `GIFTMIND_TEAM_PASSCODE`.

Multipart fields:

- `description`: up to 8,000 characters of factual observations and collector context.
- `gift_type_code`: `auto`, `product`, or `activity`.
- `lifecycle_status`: `draft` by default; also accepts `active` or `inactive`.
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

For activities, use `activityDetails` fields such as `activityMode`, `serviceRegions`, `durationMinutesMin`, `durationMinutesMax`, `participantsMin`, `participantsMax`, `pricingUnit`, and `bookingRequired`.

## Response

Success is HTTP 201 with:

- `gift`: the persisted typed database record.
- `images`: stored image records; the first image is the cover.
- `analysis.source`: `deepseek` or deterministic `rule` fallback.
- `analysis.confidence`: aggregate suggestion confidence.
- `analysis.questions`: facts still worth human confirmation.
- `analysis.sourceRefs`: compact extraction status for links and images.

Exact duplicates return HTTP 409 with `detail.code = DUPLICATE_GIFT`. Insufficient or invalid data returns HTTP 422 with validation errors and, when available, follow-up questions.

## Counts

`GET /api/agent/gifts/counts` returns current non-deleted records as `productCount`, `activityCount`, `totalCount`, and `byStatus` (`draft`, `active`, `inactive`). It uses the same authenticated session.
