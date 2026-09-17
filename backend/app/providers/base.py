from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    remaining_tokens: int | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMProvider(Protocol):
    @property
    def usage(self) -> LLMUsage: ...

    async def generate_text(self, prompt: str, system_prompt: str | None = None) -> str: ...

    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...