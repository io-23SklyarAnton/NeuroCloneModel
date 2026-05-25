__all__ = ["IInferenceEngine"]

import abc
from typing import Optional


class IInferenceEngine(abc.ABC):
    @abc.abstractmethod
    async def generate_async(
            self,
            system_prompt: str,
            user_prompt: str,
            lora_path: Optional[str],
            max_tokens: int,
            temp: float,
            priority: int,
            assistant_prefill: str = "",
    ) -> str: ...

    @abc.abstractmethod
    async def train_lora(
            self,
            train_data_path: str,
            adapter_path: str,
    ) -> None: ...
