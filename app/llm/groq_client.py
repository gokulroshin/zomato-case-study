"""Groq API client — wraps the OpenAI-compatible SDK for Groq.

Uses ``openai.OpenAI`` with ``base_url="https://api.groq.com/openai/v1"``
so that the standard chat completions interface works with Groq's hosted
Llama models.

Features:
    - Reads API key and model config from ``app.config.settings``.
    - 1 automatic retry on timeout / 5xx errors.
    - Returns the raw ``ChatCompletion`` response for downstream parsing.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam

from app.config import settings

logger = logging.getLogger(__name__)

# Groq's OpenAI-compatible endpoint.
_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqClient:
    """Thin wrapper around the OpenAI SDK configured for Groq.

    Parameters
    ----------
    api_key :
        Override the API key (useful for testing). Falls back to
        ``settings.groq_api_key``.
    model :
        Override the model name. Falls back to ``settings.groq_model``.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self._client = OpenAI(
            api_key=self._api_key,
            base_url=_GROQ_BASE_URL,
            timeout=settings.groq_timeout_seconds,
        )

    # ── Public API ─────────────────────────────────────────────

    def chat(
        self,
        messages: List[ChatCompletionMessageParam],
        *,
        temperature: float | None = None,
        max_tokens: int = 2048,
    ) -> str:
        """Send a chat completion request and return the assistant content.

        Retries once on transient errors (timeout, 5xx, rate limit).

        Parameters
        ----------
        messages :
            The conversation messages in OpenAI format.
        temperature :
            Sampling temperature override. Defaults to
            ``settings.groq_temperature``.
        max_tokens :
            Maximum tokens in the response.

        Returns
        -------
        str
            The text content of the assistant's reply.

        Raises
        ------
        GroqError
            If the request fails after all retries.
        """
        temp = temperature if temperature is not None else settings.groq_temperature
        max_retries = settings.groq_max_retries
        last_error: Exception | None = None

        for attempt in range(1 + max_retries):
            try:
                t0 = time.time()
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=max_tokens,
                )
                elapsed_ms = (time.time() - t0) * 1000
                logger.info(
                    "Groq response: model=%s, tokens=%s, latency=%.0fms",
                    self.model,
                    getattr(response.usage, "total_tokens", "?"),
                    elapsed_ms,
                )
                content = response.choices[0].message.content or ""
                return content.strip()

            except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
                last_error = exc
                if attempt < max_retries:
                    wait = 2 ** attempt  # exponential backoff: 1s, 2s, ...
                    logger.warning(
                        "Groq request failed (attempt %d/%d): %s. "
                        "Retrying in %ds ...",
                        attempt + 1,
                        1 + max_retries,
                        exc,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "Groq request failed after %d attempts: %s",
                        1 + max_retries,
                        exc,
                    )

        raise GroqError(
            f"Groq API call failed after {1 + max_retries} attempts"
        ) from last_error


class GroqError(Exception):
    """Raised when the Groq API call fails after all retries."""
