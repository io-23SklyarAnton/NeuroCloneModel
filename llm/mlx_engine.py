import asyncio
from typing import Optional
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

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
        self.load_base_model(base_model)

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
            system_prompt: str,
            user_prompt: str,
            lora_path: Optional[str],
            max_tokens: int,
            temp: float,
            assistant_prefill: str = "",
    ) -> str:
        if lora_path != self._active_lora_path:
            self._apply_adapter(lora_path)
            self._active_lora_path = lora_path

        sampler = make_sampler(temp=temp)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        formatted_prompt = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        formatted_prompt += assistant_prefill

        return generate(
            self._model,
            self._tokenizer,
            prompt=formatted_prompt,
            max_tokens=max_tokens,
            sampler=sampler,
            verbose=False
        )

    def _apply_adapter(
            self,
            lora_path: Optional[str],
    ):
        pass

    async def generate_async(
            self,
            system_prompt: str,
            user_prompt: str,
            lora_path: Optional[str],
            max_tokens: int,
            temp: float,
            assistant_prefill: str = "",
    ) -> str:
        async with self._lock:
            return await asyncio.to_thread(
                self._sync_generate,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                lora_path=lora_path,
                max_tokens=max_tokens,
                temp=temp,
                assistant_prefill=assistant_prefill
            )
