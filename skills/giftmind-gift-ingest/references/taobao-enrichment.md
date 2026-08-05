# Taobao and Tmall enrichment

Use this workflow only for gift research and evidence collection. Do not mutate the user's Taobao account.

## Collect the product identity

1. Use the exact Taobao/Tmall URL supplied by the user. Otherwise run `search_products` with `sourceApp` and save the complete result with `-o`.
2. Match the candidate by title, shop, item ID, visible image, and the user's description. Do not match on price alone.
3. Open the exact returned URL or click the matched non-SKU product element. Never invent a product URL.
4. Read the detail page and capture the canonical title, shop name, item ID, main image, visible product form, and explicit product statements.

## Resolve the target SKU

1. Run `get_product_skus` for the current product or exact item ID.
2. Match every SKU dimension against explicit user intent, such as color, size, capacity, bundle, edition, or service period.
3. If one dimension remains ambiguous and changes price or product identity, show the available options, including SKU images after removing any trailing `_.webp`, and ask the user.
4. Run `scan_page_elements` without a filter and save the complete DOM with `-o`.
5. Find the exact SKU element index. Click it with `click_element` using `index`; never use text matching for SKU selection.
6. Repeat for each SKU dimension and confirm the selected values with `get_product_skus` when possible.

## Observe the real price

1. Wait at least 3 seconds after the final SKU click.
2. Run `scan_page_elements` with a `￥` or price filter.
3. Associate the refreshed price with the selected SKU and reject unrelated crossed-out, coupon, installment, add-on, or recommendation prices.
4. Record one exact CNY value only when the association is unambiguous. Otherwise leave the price unset and record the ambiguity.
5. Record the observation time in ISO 8601 with a timezone.

Search-card prices, `￥xx 起`, coupon thresholds, and default prices are not valid exact-SKU evidence.

## Collect additional facts

Capture only explicit detail-page or SKU facts:

- product title, generic form, brand, and shop;
- item ID, trusted product URL, and selected SKU map;
- materials, colors, sizes, capacity, model, included components, and compatibility;
- personalization options and required input;
- stock state, shipping promise, return risk, and warranty statements;
- main and selected-SKU images;
- a small review summary only when the user requests it or it materially affects suitability.

Do not infer a material from appearance, a brand from visual similarity, or a shipping/warranty promise from store reputation.

## Map evidence into GiftMind

Pass the observed price and source metadata through the client:

```powershell
python scripts/ingest_gift.py `
  --name '<canonical title>' `
  --source-url '<exact returned URL>' `
  --generic-product-name '<product form>' `
  --material '<verified material>' `
  --color '<selected color>' `
  --size '<selected size>' `
  --variant-notes '<remaining variants or limitations>' `
  --taobao-shop-name '<shop>' `
  --taobao-item-id '<item ID>' `
  --taobao-sku '<dimension>=<selected value>' `
  --taobao-price '<exact refreshed price>' `
  --taobao-observed-at '<ISO-8601 timestamp>'
```

Use `--specifications-json` for capacity, model, bundle contents, compatibility, or other structured facts. The client stores provenance in `productDetails.specifications.taobaoEvidence` and `sourceNotes`.

If `taobao-native` cannot reach or operate the detail page, keep the source URL, title, images, and other supported facts, but omit exact price and explain which step failed.
