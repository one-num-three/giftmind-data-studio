# Local gift analysis

Prepare `knownFields` locally before ingestion. Do not ask the server to infer routine fields.

## Separate facts from judgments

Facts require user statements, visible image evidence, or a trusted source:

- canonical product/activity identity;
- price, currency, selected SKU, dimensions, materials, colors, compatibility, and included items;
- merchant, source URL, shipping, return, warranty, booking, and availability statements.

Local judgments may be generated from those facts but remain suggestions:

- recipient types, interests, traits, occasions, desired feelings, and tags;
- why it works as a gift, best and unsuitable scenarios;
- purchase, ritual, pairing, and presentation ideas;
- taboo, allergy, safety, or mismatch warnings.

Never turn a judgment into an observed fact. Record important provenance and uncertainty in `sourceNotes`, `collectorNotes`, or type-specific notes.

## Build a useful draft

Populate as many supported fields as the evidence justifies:

```json
{
  "canonicalName": "礼物名称",
  "shortDescription": "基于证据的简短中文描述",
  "giftTypeCode": "product",
  "recipientTypes": ["朋友"],
  "ageRanges": [],
  "traits": [],
  "interests": [],
  "occasions": ["生日"],
  "desiredFeelings": ["被重视"],
  "tags": ["实用礼物"],
  "priceMin": 158,
  "priceMax": 158,
  "currency": "CNY",
  "whyTemplate": "说明它为什么适合，并区分事实与判断。",
  "bestScenarios": "适合的关系、场合和使用情境。",
  "unsuitableScenarios": "可能不合适的偏好、限制或风险。",
  "purchaseOrBookingTip": "购买前需要核对的规格和履约信息。",
  "ritualTip": "符合关系阶段的赠送方式。",
  "pairingIdeas": "贺卡、包装或搭配建议。",
  "sourceNotes": "列明用户、图片、淘宝详情页等证据来源。",
  "collectorNotes": "列明仍未确认的事实和本地判断。",
  "confidenceLevel": "medium",
  "productDetails": {
    "productForm": "physical",
    "genericProductName": "通用商品类型",
    "materials": [],
    "colors": [],
    "sizes": [],
    "specifications": {},
    "variantNotes": "规格与不确定项",
    "shippingRequired": true
  }
}
```

For activities, replace `productDetails` with `activityDetails` and include mode, category, regions, duration, participant count, pricing unit, booking, restrictions, included items, and cancellation expectations when supported.

Do not set `verifiedAt`. Human review owns verification.

## Submit

Write the object to a temporary UTF-8 JSON file in an authorized workspace, pass it with `--known-json`, and delete the temporary file after a successful or terminal response. Keep the default `--analysis-mode local`.
