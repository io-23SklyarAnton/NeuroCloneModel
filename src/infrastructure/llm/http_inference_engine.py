__all__ = ["HttpInferenceEngine"]

from typing import Any, Optional

import aiohttp

from infrastructure.llm.i_inference_engine import IInferenceEngine


_DEFAULT_GENERATE_TIMEOUT_SECONDS: float = 120.0


class HttpInferenceEngine(IInferenceEngine):
    def __init__(
            self,
            base_url: str,
            generate_timeout_seconds: float = _DEFAULT_GENERATE_TIMEOUT_SECONDS,
            train_timeout_seconds: Optional[float] = None,
    ) -> None:
        self._base_url: str = base_url.rstrip("/")
        self._generate_timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(
            total=generate_timeout_seconds,
        )
        self._train_timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(
            total=train_timeout_seconds,
        )

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
        payload: dict[str, Any] = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "lora_path": lora_path,
            "max_tokens": max_tokens,
            "temp": temp,
            "priority": priority,
            "assistant_prefill": assistant_prefill,
        }

        async with aiohttp.ClientSession(timeout=self._generate_timeout) as session:
            async with session.post(
                f"{self._base_url}/generate",
                json=payload,
            ) as response:
                response.raise_for_status()
                data: dict[str, Any] = await response.json()
                return data["text"]

    async def train_lora(
            self,
            train_data_path: str,
            adapter_path: str,
    ) -> None:
        payload: dict[str, Any] = {
            "train_data_path": train_data_path,
            "adapter_path": adapter_path,
        }

        async with aiohttp.ClientSession(timeout=self._train_timeout) as session:
            async with session.post(
                f"{self._base_url}/train_lora",
                json=payload,
            ) as response:
                response.raise_for_status()
                await response.read()
