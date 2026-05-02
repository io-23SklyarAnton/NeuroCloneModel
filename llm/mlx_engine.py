import asyncio
from typing import Optional
from mlx_lm import load, generate

from llm.i_inference_engine import IInferenceEngine
import constants

MODEL_PATHS = {
    constants.AvailableModel.QWEN_3_5_9B: "mlx-community/Qwen3.5-9B-OptiQ-4bit",
}


class MLXInferenceEngine(IInferenceEngine):
    def __init__(
            self,
            base_model: constants.AvailableModel,
    ):
        self._base_model_path = base_model
        self._model = None
        self._tokenizer = None
        self._active_lora_path: Optional[str] = None

        self._lock = asyncio.Lock()

    def load_base_model(
            self,
            base_model: constants.AvailableModel,
    ) -> None:
        base_model_path: str = MODEL_PATHS.get(base_model)
        if base_model_path is None:
            raise ValueError(f"Unsupported model: {base_model}")

        self._model, self._tokenizer = load(base_model_path)

    def _sync_generate(
            self,
            prompt: str,
            lora_path: Optional[str],
            max_tokens: int,
            temp: float,
    ) -> str:
        if lora_path != self._active_lora_path:
            self._apply_adapter(lora_path)
            self._active_lora_path = lora_path

        return generate(
            self._model,
            self._tokenizer,
            prompt,
            max_tokens=max_tokens,
            temp=temp
        )

    def _apply_adapter(
            self,
            lora_path: Optional[str],
    ):
        pass

    async def generate_async(
            self,
            prompt: str,
            lora_path: Optional[str],
            max_tokens: int,
            temp: float,
    ) -> str:
        async with self._lock:
            return await asyncio.to_thread(
                self._sync_generate,
                prompt=prompt,
                lora_path=lora_path,
                max_tokens=max_tokens,
                temp=temp,
            )
