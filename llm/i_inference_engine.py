from abc import ABC, abstractmethod
from typing import Optional


class IInferenceEngine(ABC):
    @abstractmethod
    async def generate_async(
            self,
            system_prompt: str,
            user_prompt: str,
            lora_path: Optional[str],
            max_tokens: int,
            temp: float,
            priority: int,
            assistant_prefill: str = "",
    ) -> str:
        pass

    @abstractmethod
    async def train_lora(
            self,
            data_dir: str,
            adapter_path: str,
    ) -> None:
        pass
