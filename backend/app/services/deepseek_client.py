"""Shared, auditable DeepSeek JSON client.

The client owns transport retries and one schema-repair attempt. Callers own
business fallbacks: an unavailable model must never silently relax a product
constraint.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from time import monotonic
from typing import Any
from uuid import uuid4

import httpx
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import Settings, get_settings
from backend.app.models.operations import AIRun


class DeepSeekError(Exception):
    """A stable model-service error safe for orchestration code to inspect."""

    def __init__(self, error_type: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable


class DeepSeekNotConfiguredError(DeepSeekError):
    def __init__(self) -> None:
        super().__init__("not_configured", "DeepSeek API key is not configured")


class DeepSeekResponseError(DeepSeekError):
    """The provider answered, but the body could not satisfy the contract."""


@dataclass(frozen=True, slots=True)
class DeepSeekUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class DeepSeekJSONResult:
    data: BaseModel | dict[str, Any]
    model: str
    operation: str
    prompt_version: str
    request_id: str
    usage: DeepSeekUsage
    duration_ms: int
    repaired: bool
    provider_attempts: int


class DeepSeekClient:
    """Call DeepSeek's OpenAI-compatible endpoint and return validated JSON."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http_client = http_client

    @property
    def configured(self) -> bool:
        return bool((self.settings.deepseek_api_key or "").strip())

    async def complete_json(
        self,
        *,
        operation: str,
        prompt_version: str,
        system_prompt: str,
        user_payload: dict[str, Any] | list[Any] | str,
        output_model: type[BaseModel] | None = None,
        schema_hint: str | None = None,
        temperature: float = 0.1,
        session: AsyncSession | None = None,
        gift_id: str | None = None,
    ) -> DeepSeekJSONResult:
        """Return one JSON object, repairing invalid JSON/schema exactly once."""

        if not self.configured:
            raise DeepSeekNotConfiguredError()
        if not operation.strip() or not prompt_version.strip():
            raise ValueError("operation and prompt_version are required")

        started = monotonic()
        request_id = str(uuid4())
        provider_attempts = 0
        repaired = False
        usage = DeepSeekUsage()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._serialize_user_payload(user_payload)},
        ]

        try:
            content, usage, attempts = await self._request(messages, temperature)
            provider_attempts += attempts
            try:
                data = self._validate_content(content, output_model)
            except DeepSeekResponseError as first_error:
                repaired = True
                repair_messages = [
                    *messages,
                    {"role": "assistant", "content": content[:12000]},
                    {
                        "role": "user",
                        "content": self._repair_instruction(first_error, schema_hint),
                    },
                ]
                content, repair_usage, attempts = await self._request(repair_messages, 0)
                provider_attempts += attempts
                usage = self._combine_usage(usage, repair_usage)
                data = self._validate_content(content, output_model)
        except DeepSeekError as exc:
            duration_ms = max(0, round((monotonic() - started) * 1000))
            await self._record_run(
                session=session,
                gift_id=gift_id,
                operation=operation,
                prompt_version=prompt_version,
                request_id=request_id,
                success=False,
                duration_ms=duration_ms,
                usage=usage,
                repaired=repaired,
                provider_attempts=provider_attempts,
                error_type=exc.error_type,
            )
            raise

        duration_ms = max(0, round((monotonic() - started) * 1000))
        await self._record_run(
            session=session,
            gift_id=gift_id,
            operation=operation,
            prompt_version=prompt_version,
            request_id=request_id,
            success=True,
            duration_ms=duration_ms,
            usage=usage,
            repaired=repaired,
            provider_attempts=provider_attempts,
            error_type=None,
        )
        return DeepSeekJSONResult(
            data=data,
            model=self.settings.deepseek_model,
            operation=operation,
            prompt_version=prompt_version,
            request_id=request_id,
            usage=usage,
            duration_ms=duration_ms,
            repaired=repaired,
            provider_attempts=provider_attempts,
        )

    async def _request(
        self,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> tuple[str, DeepSeekUsage, int]:
        payload = {
            "model": self.settings.deepseek_model,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": messages,
        }
        endpoint = f"{self.settings.deepseek_base_url.rstrip('/')}/chat/completions"
        attempts = 0
        for attempts, retry_index in enumerate(range(self.settings.deepseek_max_retries + 1), start=1):
            try:
                if self._http_client is not None:
                    response = await self._http_client.post(
                        endpoint,
                        headers=self._headers(),
                        json=payload,
                    )
                else:
                    async with httpx.AsyncClient(timeout=self.settings.deepseek_timeout_seconds) as client:
                        response = await client.post(
                            endpoint,
                            headers=self._headers(),
                            json=payload,
                        )
                self._raise_for_status(response)
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise DeepSeekResponseError("empty_response", "DeepSeek returned empty content")
                return content, self._read_usage(body), attempts
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                error = DeepSeekError("timeout" if isinstance(exc, httpx.TimeoutException) else "transport", str(exc), retryable=True)
            except DeepSeekError as exc:
                error = exc
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise DeepSeekResponseError("malformed_response", "DeepSeek returned an unexpected response envelope") from exc

            if not error.retryable or retry_index >= self.settings.deepseek_max_retries:
                raise error
            await asyncio.sleep(min(0.25 * (2**retry_index), 1.0))

        raise DeepSeekError("unknown", "DeepSeek request failed")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _serialize_user_payload(payload: dict[str, Any] | list[Any] | str) -> str:
        if isinstance(payload, str):
            return payload
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)

    @staticmethod
    def _validate_content(content: str, output_model: type[BaseModel] | None) -> BaseModel | dict[str, Any]:
        try:
            parsed = parse_json_object(content)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise DeepSeekResponseError("invalid_json", "DeepSeek did not return a valid JSON object") from exc
        if output_model is None:
            return parsed
        try:
            return output_model.model_validate(parsed)
        except ValidationError as exc:
            raise DeepSeekResponseError("schema_validation", "DeepSeek JSON did not match the output schema") from exc

    @staticmethod
    def _repair_instruction(error: DeepSeekError, schema_hint: str | None) -> str:
        hint = schema_hint or "Return the same intended answer as one valid JSON object with every required field."
        return (
            "Your previous response failed validation. Fix only its JSON syntax or schema; do not add new facts. "
            f"Validation error: {error.error_type}. Required contract: {hint} "
            "Return one JSON object only, with no Markdown fence or commentary."
        )

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        status = response.status_code
        if 200 <= status < 300:
            return
        mapping = {
            401: ("authentication", False),
            402: ("quota", False),
            403: ("permission", False),
            429: ("rate_limit", True),
        }
        error_type, retryable = mapping.get(status, ("upstream" if status >= 500 else "request_rejected", status >= 500))
        raise DeepSeekError(error_type, f"DeepSeek returned HTTP {status}", retryable=retryable)

    @staticmethod
    def _read_usage(body: dict[str, Any]) -> DeepSeekUsage:
        usage = body.get("usage") or {}
        return DeepSeekUsage(
            input_tokens=_nonnegative_int(usage.get("prompt_tokens")),
            output_tokens=_nonnegative_int(usage.get("completion_tokens")),
        )

    @staticmethod
    def _combine_usage(first: DeepSeekUsage, second: DeepSeekUsage) -> DeepSeekUsage:
        return DeepSeekUsage(
            input_tokens=_sum_optional(first.input_tokens, second.input_tokens),
            output_tokens=_sum_optional(first.output_tokens, second.output_tokens),
        )

    async def _record_run(
        self,
        *,
        session: AsyncSession | None,
        gift_id: str | None,
        operation: str,
        prompt_version: str,
        request_id: str,
        success: bool,
        duration_ms: int,
        usage: DeepSeekUsage,
        repaired: bool,
        provider_attempts: int,
        error_type: str | None,
    ) -> None:
        if session is None:
            return
        session.add(
            AIRun(
                gift_id=gift_id,
                operation=operation,
                model=self.settings.deepseek_model,
                success=success,
                duration_ms=duration_ms,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                error_type=error_type,
                summary_json={
                    "promptVersion": prompt_version,
                    "requestId": request_id,
                    "repaired": repaired,
                    "providerAttempts": provider_attempts,
                },
            )
        )
        try:
            await session.commit()
        except SQLAlchemyError:
            # AI output remains usable if operational logging is temporarily down.
            await session.rollback()


def parse_json_object(content: str) -> dict[str, Any]:
    """Extract one JSON object from plain or fenced model output."""

    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("DeepSeek did not return a JSON object")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise TypeError("DeepSeek returned a non-object JSON value")
    return parsed


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _sum_optional(first: int | None, second: int | None) -> int | None:
    if first is None and second is None:
        return None
    return (first or 0) + (second or 0)
