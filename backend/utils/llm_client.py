"""
Resilient OpenAI wrapper
- Retry with exponential backoff on rate limit / transient errors
- Per-call timeout enforcement
- Cost + latency logging per call
"""
import asyncio
import time
import logging
import json
from openai import AsyncOpenAI, RateLimitError, APIStatusError

logger = logging.getLogger(__name__)

_client = AsyncOpenAI()

# Retry config
MAX_RETRIES  = 3
BASE_DELAY   = 1.5   # seconds
TIMEOUT_SEC  = 30    # max seconds per call


async def chat_completion(
    model: str,
    messages: list,
    temperature: float = 0.1,
    response_format: dict | None = None,
    caller: str = "unknown",
) -> str:
    """
    Drop-in replacement for openai client.chat.completions.create.
    Returns the raw content string of the first choice.
    Raises RuntimeError after MAX_RETRIES exhausted.
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            start = time.time()
            kwargs = dict(
                model=model,
                messages=messages,
                temperature=temperature,
                timeout=TIMEOUT_SEC,
            )
            if response_format:
                kwargs["response_format"] = response_format

            response = await _client.chat.completions.create(**kwargs)

            latency_ms = int((time.time() - start) * 1000)
            usage = response.usage
            logger.info(json.dumps({
                "event":       "llm_call",
                "caller":      caller,
                "model":       model,
                "attempt":     attempt,
                "latency_ms":  latency_ms,
                "prompt_tok":  usage.prompt_tokens if usage else None,
                "compl_tok":   usage.completion_tokens if usage else None,
            }))

            return response.choices[0].message.content

        except RateLimitError as e:
            delay = BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(f"rate_limit_retry caller={caller} attempt={attempt}/{MAX_RETRIES} delay={delay}s error={e}")
            last_error = e
            await asyncio.sleep(delay)

        except APIStatusError as e:
            if e.status_code >= 500:
                delay = BASE_DELAY * attempt
                logger.warning(f"openai_5xx caller={caller} attempt={attempt} status={e.status_code} delay={delay}s")
                last_error = e
                await asyncio.sleep(delay)
            else:
                raise  # 4xx errors should not be retried

        except asyncio.TimeoutError:
            logger.error(f"openai_timeout caller={caller} attempt={attempt} timeout={TIMEOUT_SEC}s")
            last_error = asyncio.TimeoutError(f"OpenAI call timed out after {TIMEOUT_SEC}s")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BASE_DELAY)

    raise RuntimeError(f"OpenAI call failed after {MAX_RETRIES} attempts: {last_error}")
