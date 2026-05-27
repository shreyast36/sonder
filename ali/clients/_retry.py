"""
Transient-error retry wrapper for LLM provider clients.

Why this exists
---------------
Both Anthropic (529 Overloaded) and OpenAI (429 / 500 / 502 / 503 /
504) routinely return short-lived errors that resolve on a single
retry. Without retry, every transient hiccup falls through to the
router's cross-provider fallback — which serves the user a reply
from a different model family. That's strictly worse than waiting
~1.5 seconds and getting Claude back.

What this catches
-----------------
- `anthropic.OverloadedError` (529)
- `anthropic.APIStatusError` with status_code in TRANSIENT_STATUS
- `anthropic.RateLimitError` (429 with retry-after)
- `openai.RateLimitError` (429)
- `openai.APIStatusError` with status_code in TRANSIENT_STATUS
- `openai.APITimeoutError`
- `httpx.ConnectError` / `httpx.ReadTimeout`
- Any other exception is raised immediately so the router can decide
  what to do (e.g. 401 should escalate, not retry).

Backoff
-------
Exponential with full jitter. Three attempts by default — total
worst-case wait is ~5s before the router cross-provider-falls-back.
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# HTTP status codes Anthropic / OpenAI treat as transient.
TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}


def _is_transient(exc: BaseException) -> bool:
    """True if the exception is the kind that's likely to resolve on
    a retry within ~5 seconds. False means escalate immediately."""
    name = type(exc).__name__

    # Provider-specific names, matched by class name to avoid hard
    # imports at module load (clients import this; we don't want a
    # circular dep on the SDKs).
    if name in {
        "OverloadedError",      # anthropic 529
        "RateLimitError",       # anthropic / openai 429
        "APITimeoutError",      # openai
        "InternalServerError",  # openai 500
        "APIConnectionError",   # both — network / DNS
    }:
        return True

    # Generic status-code check (anthropic.APIStatusError /
    # openai.APIStatusError both expose .status_code).
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and status in TRANSIENT_STATUS:
        return True

    # httpx connection / read timeouts surface here when an SDK call
    # transports them through.
    if name in {"ConnectError", "ReadTimeout", "ConnectTimeout"}:
        return True

    return False


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
    label: str = "llm",
) -> T:
    """Run `fn()` with exponential-backoff retry on transient errors.

    `fn` is a zero-arg coroutine factory so we can re-invoke the
    underlying SDK call cleanly each attempt. Re-raises on the final
    attempt or on a non-transient error.

    Example:
        result = await with_retry(
            lambda: client.messages.create(...),
            label="anthropic.small",
        )
    """
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except BaseException as exc:
            last_exc = exc
            if not _is_transient(exc) or attempt == attempts:
                raise
            # Exponential backoff with full jitter — wait between
            # 0 and (base_delay * 2^(attempt-1)), capped at max_delay.
            window = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay = random.uniform(0, window)
            logger.warning(
                "%s transient error (%s); attempt %d/%d, retrying in %.2fs: %s",
                label, type(exc).__name__, attempt, attempts, delay, exc,
            )
            await asyncio.sleep(delay)
    # Unreachable; the loop either returns or re-raises above.
    raise last_exc  # type: ignore[misc]
