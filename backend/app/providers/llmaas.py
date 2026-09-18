import asyncio
from collections.abc import Sequence
from time import monotonic

import httpx
from openai import AsyncOpenAI

from app.core.config import Settings
from app.providers.base import LLMUsage
from app.services.prompting import governed_system_prompt


class LLMAASError(RuntimeError):
    """A safe LLMAAS error that never includes credentials or response bodies."""


def _normalize_json_response(answer: str) -> str:
    stripped = answer.strip().lstrip("\ufeff")
    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[0].strip().lower() in {"```", "```json"} and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped


class LLMAASProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.llm_api_key or not settings.llmaas_client_id or not settings.llmaas_client_secret:
            raise ValueError("LLMAAS credentials are not configured")
        self._settings = settings
        self._api_client_key = settings.llm_api_key.get_secret_value()
        self._client_secret = settings.llmaas_client_secret.get_secret_value()
        self._access_token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = asyncio.Lock()
        self._input_tokens = 0
        self._output_tokens = 0
        self._remaining_tokens: int | None = None

    @property
    def usage(self) -> LLMUsage:
        return LLMUsage(self._input_tokens, self._output_tokens, self._remaining_tokens)

    def _record_usage(self, usage: object | None, headers: object) -> None:
        self._input_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
        self._output_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        for header in (
            "x-ratelimit-remaining-tokens",
            "x-llm-rate-limit-remaining-tokens",
            "x-quota-remaining-tokens",
        ):
            value = headers.get(header) if hasattr(headers, "get") else None
            if value is not None:
                try:
                    self._remaining_tokens = int(str(value).replace(",", ""))
                except ValueError:
                    continue
                break

    async def _get_token(self) -> str:
        if self._access_token and monotonic() < self._token_expires_at:
            return self._access_token
        async with self._token_lock:
            if self._access_token and monotonic() < self._token_expires_at:
                return self._access_token
            try:
                async with httpx.AsyncClient(timeout=self._settings.llm_timeout_seconds) as client:
                    response = await client.post(
                        self._settings.llmaas_token_url,
                        data={
                            "client_id": self._settings.llmaas_client_id,
                            "client_secret": self._client_secret,
                            "grant_type": "client_credentials",
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
            except (httpx.HTTPError, ValueError) as error:
                raise LLMAASError("LLMAAS authentication failed") from error

            token = payload.get("access_token")
            if not isinstance(token, str) or not token:
                raise LLMAASError("LLMAAS authentication returned no access token")
            expires_in = payload.get("expires_in", 300)
            lifetime = int(expires_in) if isinstance(expires_in, (int, str)) else 300
            self._access_token = token
            self._token_expires_at = monotonic() + max(lifetime - 30, 30)
            return token

    async def _client(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=await self._get_token(),
            base_url=self._settings.llm_base_url,
            default_headers={"X-LLM-API-CLIENT-ID": f"Bearer {self._api_client_key}"},
            timeout=self._settings.llm_timeout_seconds,
            max_retries=1,
        )

    async def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = [{"role": "system", "content": governed_system_prompt(system_prompt)}]
        messages.append({"role": "user", "content": prompt})
        try:
            client = await self._client()
            request_options = {
                "model": self._settings.llm_model,
                "messages": messages,
                "response_format": {"type": "json_object"},
            }
            if not self._settings.llm_model.startswith("gpt-5"):
                request_options["temperature"] = 0.0
            raw_response = await client.chat.completions.with_raw_response.create(
                **request_options,
            )
            response = raw_response.parse()
            self._record_usage(response.usage, raw_response.headers)
        except LLMAASError:
            raise
        except (httpx.TimeoutException, asyncio.TimeoutError) as error:
            raise LLMAASError("LLMAAS text generation timed out") from error
        except Exception as error:
            raise LLMAASError("LLMAAS text generation failed") from error
        answer = response.choices[0].message.content
        if not answer:
            raise LLMAASError("LLMAAS returned an empty response")
        return _normalize_json_response(answer)

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            client = await self._client()
            raw_response = await client.embeddings.with_raw_response.create(
                model=self._settings.llm_embedding_model,
                input=list(texts),
                encoding_format="float",
            )
            response = raw_response.parse()
            self._record_usage(response.usage, raw_response.headers)
        except LLMAASError:
            raise
        except Exception as error:
            raise LLMAASError("LLMAAS embedding failed") from error
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]