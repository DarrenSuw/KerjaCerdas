"""Shared factory for Gemini chat LLMs with a rate-limit fallback chain.

Free-tier Gemini keys are throttled per model (RPM). Instead of stalling on
long SDK retries against one model, we build a LangChain fallback chain:

    gemini-3.1-flash-lite (15 RPM)  — primary
    gemini-3.5-flash-lite (15 RPM)  — first fallback
    gemini-3.6-flash      (5 RPM)   — last resort

Each model gets at most ONE quick SDK retry (max_retries=1) so a 429 fails
over to the next model in seconds rather than blocking for 30s+ of backoff.

Every chat call site should use `build_chat_llm()` instead of constructing
ChatGoogleGenerativeAI directly, so the chain (and API-key resolution) stays
consistent app-wide.
"""

from __future__ import annotations

import logging
import os
import time

from langchain_core.runnables import Runnable, RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.app.config.settings import settings
from backend.app.services.privacy.redact import redact_llm_input

logger = logging.getLogger(__name__)


class LLMBusyError(RuntimeError):
    """All chat models are unavailable (throttled/failing); callers should degrade gracefully."""


# --- Circuit breaker -------------------------------------------------------
# When the whole fallback chain fails, hitting every model again on the very
# next request only burns more RPM. Trip a short breaker so subsequent calls
# fail fast (LLMBusyError) without any network calls until the cooldown ends.
_BREAKER_COOLDOWN_S = 30.0
_breaker_open_until = 0.0


def _breaker_remaining() -> float:
    return _breaker_open_until - time.monotonic()


def _trip_breaker() -> None:
    global _breaker_open_until
    _breaker_open_until = time.monotonic() + _BREAKER_COOLDOWN_S
    logger.warning("LLM circuit breaker tripped — failing fast for %.0fs", _BREAKER_COOLDOWN_S)


def reset_breaker() -> None:
    """Test hook / manual reset."""
    global _breaker_open_until
    _breaker_open_until = 0.0


def _is_availability_error(exc: BaseException) -> bool:
    """True for throttling / transient provider outages (429, 5xx, timeouts)."""
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        text = str(cur).lower()
        if any(
            marker in text
            for marker in (
                "429",
                "resource_exhausted",
                "quota",
                "rate limit",
                "503",
                "unavailable",
                "500",
                "internal",
                "timeout",
                "timed out",
                "deadline",
                "connection",
            )
        ):
            return True
        cur = cur.__cause__ or cur.__context__
    return False


def resolve_gemini_key() -> str:
    """ChatGoogleGenerativeAI only reads env vars / explicit api_key — resolve like the embedder."""
    return (
        settings.gemini_api_key
        or os.environ.get("GEMINI_API_KEY", "")
        or os.environ.get("GOOGLE_API_KEY", "")
    )


def chat_model_chain() -> list[str]:
    """Primary model followed by fallbacks, de-duplicated, order preserved."""
    seen: set[str] = set()
    chain: list[str] = []
    for m in [settings.gemini_chat_model, *settings.gemini_chat_fallback_models]:
        if m and m not in seen:
            seen.add(m)
            chain.append(m)
    return chain


def _usage(result) -> tuple[int, int, str]:
    meta = getattr(result, "usage_metadata", None) or {}
    model = (getattr(result, "response_metadata", None) or {}).get("model_name", "")
    return int(meta.get("input_tokens", 0) or 0), int(meta.get("output_tokens", 0) or 0), model


def build_chat_llm(temperature: float = 0.4, task: str = "chat", **kwargs) -> Runnable:
    """Build a chat LLM that fails over across the model chain on errors (e.g. 429).

    Returns a Runnable supporting .invoke/.ainvoke with the same message
    interface as ChatGoogleGenerativeAI. Async calls are logged to `ai_logs`
    (task, model, tokens) for the admin cost-per-action report.
    """
    api_key = resolve_gemini_key()
    if not api_key:
        # Passing api_key=None lets ChatGoogleGenerativeAI's underlying client
        # fall back to Application Default Credentials (gcloud/service-account
        # discovery) instead of failing cleanly — this deployment only ever
        # authenticates via GEMINI_API_KEY, so that fallback would just crash
        # with a confusing google.auth.exceptions.DefaultCredentialsError
        # instead of a clear, catchable error. Mirrors GeminiEmbedder's
        # equivalent guard (embeddings/gemini.py's _client_or_raise).
        raise RuntimeError("No Gemini auth configured (set GEMINI_API_KEY)")
    llms = [
        ChatGoogleGenerativeAI(
            model=m,
            temperature=temperature,
            api_key=api_key,
            max_retries=1,  # fail over fast instead of long same-model backoff
            timeout=30,
            **kwargs,
        )
        for m in chat_model_chain()
    ]
    chain: Runnable = llms[0] if len(llms) == 1 else llms[0].with_fallbacks(llms[1:])

    def _check_breaker() -> None:
        remaining = _breaker_remaining()
        if remaining > 0:
            raise LLMBusyError(f"LLM circuit breaker open for another {remaining:.0f}s")

    def _handle_failure(exc: Exception) -> None:
        # Only availability-class failures (429/5xx/timeouts) open the breaker;
        # persistent misconfiguration (auth, bad request) should not be masked
        # as "busy" for repeated 30s windows. Either way the caller gets
        # LLMBusyError so the API degrades instead of crashing.
        if _is_availability_error(exc):
            _trip_breaker()
        raise LLMBusyError("All chat models failed") from exc

    def _guarded_invoke(value, config=None):
        _check_breaker()
        try:
            # Breaker closes by cooldown expiry only — success never resets it,
            # so a slow success can't race a concurrent failure's trip.
            # PII is stripped by fixed rules before the prompt leaves the
            # server; prompt-level "don't repeat personal data" is only a
            # second layer (see services/privacy/redact.py).
            return chain.invoke(redact_llm_input(value), config=config)
        except LLMBusyError:
            raise
        except Exception as exc:
            _handle_failure(exc)

    async def _guarded_ainvoke(value, config=None):
        from backend.app.db.postgres_store import record_ai_usage

        _check_breaker()
        started = time.monotonic()
        try:
            result = await chain.ainvoke(redact_llm_input(value), config=config)
        except LLMBusyError:
            raise
        except Exception as exc:
            await record_ai_usage(
                task, chat_model_chain()[0], 0, 0, int((time.monotonic() - started) * 1000),
                success=False, error=str(exc),
            )
            _handle_failure(exc)
        tin, tout, model = _usage(result)
        await record_ai_usage(
            task, model or chat_model_chain()[0], tin, tout, int((time.monotonic() - started) * 1000)
        )
        return result

    return RunnableLambda(_guarded_invoke, afunc=_guarded_ainvoke)
