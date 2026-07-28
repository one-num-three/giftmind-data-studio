import httpx

from backend.app.services.source_extraction import (
    extract_public_page,
    extract_urls,
    is_public_http_url,
)


def public_resolver(*_args, **_kwargs):
    return [(2, 1, 6, "", ("93.184.216.34", 0))]


def private_resolver(*_args, **_kwargs):
    return [(2, 1, 6, "", ("127.0.0.1", 0))]


def test_extract_urls_deduplicates_and_limits_to_three():
    text = " ".join(
        [
            "https://a.test/x",
            "https://a.test/x",
            "https://b.test",
            "https://c.test/path.",
            "https://d.test",
        ]
    )

    assert extract_urls(text) == [
        "https://a.test/x",
        "https://b.test",
        "https://c.test/path",
    ]


def test_public_url_validation_rejects_local_and_non_http_destinations():
    assert is_public_http_url("file:///etc/passwd", resolver=public_resolver) is False
    assert is_public_http_url("http://localhost/admin", resolver=public_resolver) is False
    assert is_public_http_url("http://example.com", resolver=private_resolver) is False
    assert is_public_http_url("https://example.com/item", resolver=public_resolver) is True


def test_extract_public_page_returns_title_description_text_price_and_json_ld():
    html = """
    <html><head>
      <title>黄铜书签礼盒</title>
      <meta name="description" content="适合送给爱阅读的朋友">
      <script type="application/ld+json">
        {"@type":"Product","name":"黄铜书签","offers":{"price":"69.00","priceCurrency":"CNY"}}
      </script>
      <style>ignore me</style>
    </head><body>
      <h1>南京主题黄铜书签</h1>
      <p>礼盒价 ¥69，可刻字。</p>
      <script>alert("ignore")</script>
    </body></html>
    """

    async def exercise():
        transport = httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                text=html,
            )
        )
        async with httpx.AsyncClient(transport=transport) as client:
            return await extract_public_page(
                "https://example.com/gift",
                client,
                resolver=public_resolver,
            )

    import asyncio

    result = asyncio.run(exercise())
    assert result["status"] == "ok"
    assert result["title"] == "黄铜书签礼盒"
    assert result["description"] == "适合送给爱阅读的朋友"
    assert "礼盒价 ¥69" in result["text"]
    assert "ignore me" not in result["text"]
    assert result["structuredData"][0]["name"] == "黄铜书签"
    assert result["priceHints"] == ["69", "69.00"]


def test_blocked_page_becomes_a_source_result_instead_of_raising():
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: httpx.Response(500))) as client:
            return await extract_public_page(
                "http://localhost/private",
                client,
                resolver=public_resolver,
            )

    import asyncio

    result = asyncio.run(exercise())
    assert result["status"] == "blocked"
    assert result["url"] == "http://localhost/private"
