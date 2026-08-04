from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.core.config import Settings
from backend.app.models.base import Base
from backend.app.models.operations import AIRun
from backend.app.services.deepseek_client import (
    DeepSeekClient,
    DeepSeekError,
    DeepSeekNotConfiguredError,
    DeepSeekResponseError,
    parse_json_object,
)


class Answer(BaseModel):
    answer: str


class QueueClient:
    def __init__(self, *items: httpx.Response | Exception) -> None:
        self.items = list(items)
        self.requests: list[dict] = []

    async def post(self, url: str, **kwargs) -> httpx.Response:
        self.requests.append({"url": url, **kwargs})
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def settings(**overrides) -> Settings:
    values = {
        "app_secret": "test-app-secret",
        "team_passcode": "test-team-passcode",
        "deepseek_api_key": "sk-test-key",
        "deepseek_base_url": "https://deepseek.test/v1/",
        "deepseek_model": "test-json-model",
        "deepseek_timeout_seconds": 5,
        "deepseek_max_retries": 0,
    }
    values.update(overrides)
    return Settings(**values)


def response(
    content: str,
    *,
    status_code: int = 200,
    input_tokens: int = 3,
    output_tokens: int = 2,
) -> httpx.Response:
    request = httpx.Request("POST", "https://deepseek.test/v1/chat/completions")
    body = {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": input_tokens, "completion_tokens": output_tokens},
    }
    return httpx.Response(status_code, request=request, json=body)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_complete_json_uses_config_and_records_safe_trace(db_session):
    transport = QueueClient(response('{"answer":"ok"}'))
    client = DeepSeekClient(settings(), http_client=transport)

    result = await client.complete_json(
        operation="unit_test",
        prompt_version="unit_v1",
        system_prompt="Return JSON",
        user_payload={"privateMemory": "do not persist me"},
        output_model=Answer,
        session=db_session,
    )

    assert result.data == Answer(answer="ok")
    assert result.model == "test-json-model"
    assert result.usage.input_tokens == 3
    assert result.usage.output_tokens == 2
    assert result.repaired is False
    assert transport.requests[0]["url"] == "https://deepseek.test/v1/chat/completions"
    assert transport.requests[0]["json"]["model"] == "test-json-model"
    assert transport.requests[0]["json"]["response_format"] == {"type": "json_object"}

    run = (await db_session.execute(select(AIRun))).scalar_one()
    assert run.operation == "unit_test"
    assert run.summary_json["promptVersion"] == "unit_v1"
    assert "privateMemory" not in json.dumps(run.summary_json)


@pytest.mark.asyncio
async def test_invalid_json_gets_exactly_one_repair_attempt():
    transport = QueueClient(
        response("not json"),
        response('{"answer":"fixed"}', input_tokens=4, output_tokens=1),
    )
    client = DeepSeekClient(settings(), http_client=transport)

    result = await client.complete_json(
        operation="repair_test",
        prompt_version="repair_v1",
        system_prompt="Return JSON",
        user_payload={"value": "x"},
        output_model=Answer,
        schema_hint="{answer:string}",
    )

    assert result.data == Answer(answer="fixed")
    assert result.repaired is True
    assert result.provider_attempts == 2
    assert result.usage.input_tokens == 7
    assert len(transport.requests) == 2
    assert (
        "previous response failed validation"
        in transport.requests[1]["json"]["messages"][-1]["content"]
    )


@pytest.mark.asyncio
async def test_second_invalid_json_is_not_repaired_again():
    transport = QueueClient(response("bad one"), response("bad two"))
    client = DeepSeekClient(settings(), http_client=transport)

    with pytest.raises(DeepSeekResponseError) as exc_info:
        await client.complete_json(
            operation="repair_test",
            prompt_version="repair_v1",
            system_prompt="Return JSON",
            user_payload="input",
            output_model=Answer,
        )

    assert exc_info.value.error_type == "invalid_json"
    assert len(transport.requests) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [(401, "authentication"), (402, "quota"), (403, "permission")],
)
async def test_nonretryable_provider_errors_are_classified(status_code, error_type):
    transport = QueueClient(response("{}", status_code=status_code))
    client = DeepSeekClient(settings(deepseek_max_retries=3), http_client=transport)

    with pytest.raises(DeepSeekError) as exc_info:
        await client.complete_json(
            operation="error_test",
            prompt_version="error_v1",
            system_prompt="Return JSON",
            user_payload={},
        )

    assert exc_info.value.error_type == error_type
    assert len(transport.requests) == 1


@pytest.mark.asyncio
async def test_rate_limit_is_retried_using_configured_limit(monkeypatch):
    transport = QueueClient(
        response("{}", status_code=429), response('{"answer":"ok"}')
    )
    client = DeepSeekClient(settings(deepseek_max_retries=1), http_client=transport)

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr("backend.app.services.deepseek_client.asyncio.sleep", no_sleep)
    result = await client.complete_json(
        operation="retry_test",
        prompt_version="retry_v1",
        system_prompt="Return JSON",
        user_payload={},
        output_model=Answer,
    )

    assert result.provider_attempts == 2
    assert len(transport.requests) == 2


@pytest.mark.asyncio
async def test_timeout_is_classified_after_retry(monkeypatch):
    request = httpx.Request("POST", "https://deepseek.test/v1/chat/completions")
    transport = QueueClient(
        httpx.ReadTimeout("slow", request=request),
        httpx.ReadTimeout("still slow", request=request),
    )
    client = DeepSeekClient(settings(deepseek_max_retries=1), http_client=transport)

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr("backend.app.services.deepseek_client.asyncio.sleep", no_sleep)
    with pytest.raises(DeepSeekError) as exc_info:
        await client.complete_json(
            operation="timeout_test",
            prompt_version="timeout_v1",
            system_prompt="Return JSON",
            user_payload={},
        )

    assert exc_info.value.error_type == "timeout"
    assert len(transport.requests) == 2


@pytest.mark.asyncio
async def test_missing_key_fails_before_network_call():
    transport = QueueClient(response("{}"))
    client = DeepSeekClient(settings(deepseek_api_key=None), http_client=transport)

    with pytest.raises(DeepSeekNotConfiguredError):
        await client.complete_json(
            operation="missing_key",
            prompt_version="missing_v1",
            system_prompt="Return JSON",
            user_payload={},
        )

    assert transport.requests == []


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ('{"ok":true}', {"ok": True}),
        ('```json\n{"ok": true}\n```', {"ok": True}),
        ('Result follows: {"ok": true}', {"ok": True}),
    ],
)
def test_parse_json_object_accepts_supported_envelopes(content, expected):
    assert parse_json_object(content) == expected
