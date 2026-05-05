from abc import ABC, abstractmethod
from typing import Optional

import constants


class IInferenceEngine(ABC):
    @abstractmethod
    def load_base_model(
            self,
            base_model: constants.AvailableModel,
    ) -> None:
        pass

    @abstractmethod
    async def generate_async(
            self,
            system_prompt: str,
            user_prompt: str,
            lora_path: Optional[str],
            max_tokens: int,
            temp: float,
            assistant_prefill: str = "",
    ) -> str:
        pass
