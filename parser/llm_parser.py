# parser/llm_parser.py
import asyncio
import json
from groq import AsyncGroq
from core.config import settings
from core.logger import log, mask_query

MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]


class LLMParseError(Exception):
    """LLM parse hatası - retry'lar tükendikten sonra fırlatılır."""
    pass


class LLMParser:
    """Groq API istemcisi - yalnızca JSON parse için kullanılır."""

    def __init__(self):
        self.client = AsyncGroq(
            api_key=settings.groq_api_key
        )

    async def parse(
        self,
        user_query: str,
        system_prompt: str,
    ) -> dict:
        """Tek bir kullanıcı sorgusunu JSON'a çevir."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]
        return await self._call_with_retry(messages, user_query)

    async def parse_with_history(
        self,
        messages: list[dict],
        system_prompt: str,
    ) -> dict:
        """Clarification refinement: conversation history ile parse et."""
        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages,
        ]
        return await self._call_with_retry(full_messages, "[refinement]")

    async def _call_with_retry(
        self,
        messages: list[dict],
        query_ref: str,
    ) -> dict:
        """Exponential backoff ile retry mekanizması - 3 deneme."""
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0,
                    max_tokens=512,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content.strip()
                return json.loads(raw)

            except json.JSONDecodeError as e:
                last_error = e
                log.warning(
                    "parse_error",
                    attempt=attempt + 1,
                    error=str(e),
                    query_preview=mask_query(query_ref),
                )

            except Exception as e:
                last_error = e
                log.warning(
                    "parse_error",
                    attempt=attempt + 1,
                    error=type(e).__name__,
                    query_preview=mask_query(query_ref),
                )

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAYS[attempt])

        raise LLMParseError(f"Parse başarısız: {last_error}")
