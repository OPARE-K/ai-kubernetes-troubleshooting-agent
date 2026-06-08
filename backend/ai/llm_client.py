import time
from typing import Any

import httpx
from loguru import logger

from core.config import settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MAX_RETRIES = 2
DEFAULT_TIMEOUT_SECONDS = 25


class LLMClientError(Exception):
    """Raised when the OpenRouter API call fails."""


class LLMClient:
    """Call OpenRouter chat completions using HTTPX."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.openrouter_api_key
        self.model = model if model is not None else settings.openrouter_model
        self.timeout = timeout
        self.max_retries = max_retries

    def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise LLMClientError(
                "OPENROUTER_API_KEY is not configured. Set it in backend/.env"
            )
        if not self.model:
            raise LLMClientError(
                "OPENROUTER_MODEL is not configured. Set it in backend/.env"
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ai-kubernetes-agent.local",
            "X-Title": "AI Kubernetes Agent",
        }

        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            payload = self._build_payload(messages, use_json_mode=attempt <= 2)
            try:
                logger.info(
                    f"Calling OpenRouter model '{self.model}' (attempt {attempt}/{self.max_retries})"
                )
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{OPENROUTER_BASE_URL}/chat/completions",
                        json=payload,
                        headers=headers,
                    )

                if response.status_code == 429:
                    detail = self._safe_error_detail(response)
                    last_error = LLMClientError(
                        f"OpenRouter rate limited ({response.status_code}): {detail}"
                    )
                    logger.warning(f"OpenRouter attempt {attempt} failed: {last_error}")
                    if attempt < self.max_retries:
                        time.sleep(self._retry_delay_from_response(response, attempt))
                    continue

                if response.status_code >= 500:
                    raise LLMClientError(
                        f"OpenRouter server error ({response.status_code})"
                    )

                if response.status_code >= 400:
                    detail = self._safe_error_detail(response)
                    raise LLMClientError(
                        f"OpenRouter request failed ({response.status_code}): {detail}"
                    )

                data = response.json()
                content = self._extract_content(data)
                logger.info("OpenRouter response received successfully")
                return content

            except (httpx.TimeoutException, httpx.NetworkError, LLMClientError) as exc:
                last_error = exc
                logger.warning(f"OpenRouter attempt {attempt} failed: {exc}")
                if attempt < self.max_retries:
                    time.sleep(2 ** (attempt - 1))

        raise LLMClientError(
            f"OpenRouter failed after {self.max_retries} attempts: {last_error}"
        )

    def _build_payload(
        self, messages: list[dict[str, str]], use_json_mode: bool
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if use_json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _extract_content(self, data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMClientError(
                f"Unexpected OpenRouter response format (choices missing): keys={list(data.keys())}"
            )

        message = choices[0].get("message", {})
        content = message.get("content")

        if isinstance(content, str) and content.strip():
            return content.strip()

        if isinstance(content, list):
            text_parts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            combined = "\n".join(part for part in text_parts if part).strip()
            if combined:
                return combined

        refusal = message.get("refusal")
        if refusal:
            raise LLMClientError(f"OpenRouter model refused the request: {refusal}")

        raise LLMClientError(
            "OpenRouter returned an empty or unsupported response format"
        )

    def _retry_delay_from_response(self, response: httpx.Response, attempt: int) -> int:
        try:
            body = response.json()
            error = body.get("error", {})
            metadata = error.get("metadata", {}) if isinstance(error, dict) else {}
            retry_after = metadata.get("retry_after_seconds")
            if retry_after:
                return max(int(retry_after), 5)
        except Exception:
            pass
        return min(3 * attempt, 5)

    def _safe_error_detail(self, response: httpx.Response) -> str:
        try:
            body = response.json()
            if isinstance(body, dict) and "error" in body:
                return str(body["error"])
            return str(body)
        except Exception:
            return response.text[:300]
