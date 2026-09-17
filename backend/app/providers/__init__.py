from fastapi import Depends

from app.core.config import Settings, get_settings
from app.providers.llmaas import LLMAASProvider


def get_llm_provider(settings: Settings = Depends(get_settings)) -> LLMAASProvider:
	return LLMAASProvider(settings)


__all__ = ["LLMAASProvider", "get_llm_provider"]