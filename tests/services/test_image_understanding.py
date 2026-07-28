import base64

import pytest

from backend.app.services import image_understanding


@pytest.mark.asyncio
async def test_images_are_turned_into_ocr_and_visual_text_before_deepseek(tmp_path, monkeypatch):
    image_path = tmp_path / "gift.png"
    image_path.write_bytes(base64.b64decode("iVBORw0KGgo="))
    monkeypatch.setattr(image_understanding, "_local_paddle_ocr", lambda _path: "黄铜书签\n售价 69 元")

    class Settings:
        vision_api_key = "vision-key"
        vision_base_url = "https://vision.example/v1"
        vision_model = "vision-model"

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "一枚南京主题黄铜书签，带礼盒包装。"}}]}

    class Client:
        async def post(self, url, **kwargs):
            assert url == "https://vision.example/v1/chat/completions"
            assert kwargs["json"]["model"] == "vision-model"
            return Response()

    refs = await image_understanding.understand_images(
        [{"name": "gift.png", "mimeType": "image/png", "path": image_path}],
        Settings(),
        client=Client(),
    )

    assert refs[0]["status"] == "ok"
    assert refs[0]["ocrText"] == "黄铜书签\n售价 69 元"
    assert refs[0]["description"].startswith("一枚南京主题")
    assert "黄铜书签" in refs[0]["text"]
    assert "礼盒包装" in refs[0]["text"]


@pytest.mark.asyncio
async def test_image_processing_degrades_explicitly_when_no_processor_is_available(tmp_path, monkeypatch):
    image_path = tmp_path / "gift.webp"
    image_path.write_bytes(b"webp")
    monkeypatch.setattr(image_understanding, "_local_paddle_ocr", lambda _path: "")

    class Settings:
        vision_api_key = None
        vision_base_url = None
        vision_model = None

    refs = await image_understanding.understand_images(
        [{"name": "gift.webp", "mimeType": "image/webp", "path": image_path}],
        Settings(),
    )

    assert refs[0]["status"] == "unavailable"
    assert "未配置" in refs[0]["error"]
