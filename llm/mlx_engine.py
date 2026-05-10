import asyncio
from typing import Optional, Any
import mlx.core as mx
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
from mlx_lm.models.cache import make_prompt_cache

from llm.i_inference_engine import IInferenceEngine
import constants

MODEL_PATHS = {
    constants.AvailableModel.QWEN_3_5_9B: "mlx-community/Qwen3.5-9B-OptiQ-4bit",
    constants.AvailableModel.QWEN_3_5_4B: "mlx-community/Qwen3.5-4B-4bit",
    constants.AvailableModel.QWEN_2_5_3B: "mlx-community/Qwen2.5-3B-Instruct-4bit",
    constants.AvailableModel.QWEN_2_5_1_5B: "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
    constants.AvailableModel.LLAMA_3_2_3B: "mlx-community/Llama-3.2-3B-Instruct-4bit",
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
        self._frozen_system_prompt: Optional[str] = None
        self._frozen_cache_state: Optional[list[Any]] = None

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

    def _get_frozen_cache(
            self,
            system_prompt: str,
            sys_tokens: list[int],
    ) -> list[Any]:
        if self._frozen_system_prompt == system_prompt and self._frozen_cache_state is not None:
            new_cache = make_prompt_cache(self._model)
            for i, layer_cache in enumerate(new_cache):
                layer_cache.state = [mx.add(s, 0) for s in self._frozen_cache_state[i]]
            return new_cache

        cache = make_prompt_cache(self._model)
        prompt_array = mx.array(sys_tokens)[None]

        _ = self._model(prompt_array, cache=cache)
        mx.eval([c.state for c in cache])

        self._frozen_cache_state = []
        for c in cache:
            self._frozen_cache_state.append([mx.add(s, 0) for s in c.state])

        for state_list in self._frozen_cache_state:
            mx.eval(state_list)

        self._frozen_system_prompt = system_prompt

        return self._get_frozen_cache(system_prompt, sys_tokens)

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

        if self._base_model_path.is_qwen():
            sys_text = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        else:
            sys_messages = [{"role": "system", "content": system_prompt}]
            sys_text = self._tokenizer.apply_chat_template(
                sys_messages,
                tokenize=False,
                add_generation_prompt=False
            )
        sys_tokens = self._tokenizer.encode(sys_text)

        prompt_cache = self._get_frozen_cache(system_prompt, sys_tokens)

        full_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        full_text = self._tokenizer.apply_chat_template(
            full_messages,
            tokenize=False,
            add_generation_prompt=True
        )
        full_text += assistant_prefill
        full_tokens = self._tokenizer.encode(full_text)

        delta_tokens = full_tokens[len(sys_tokens):]

        return generate(
            self._model,
            self._tokenizer,
            prompt=delta_tokens,
            prompt_cache=prompt_cache,
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
