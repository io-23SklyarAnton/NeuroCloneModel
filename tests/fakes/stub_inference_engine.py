from collections import deque
from typing import Any, Optional
from infrastructure.llm import IInferenceEngine


class StubInferenceEngine(IInferenceEngine):

    def __init__(self, default_response: str='0') -> None:
        self._default_response = default_response
        self._scripted_responses: deque[str] = deque()
        self._train_should_raise: Optional[Exception] = None
        self.generate_calls: list[dict[str, Any]] = []
        self.train_calls: list[dict[str, Any]] = []

    async def generate_async(self, system_prompt: str, user_prompt: str, lora_path: Optional[str], max_tokens: int, temp: float, priority: int, assistant_prefill: str='') -> str:
        self.generate_calls.append({'system_prompt': system_prompt, 'user_prompt': user_prompt, 'lora_path': lora_path, 'max_tokens': max_tokens, 'temp': temp, 'priority': priority, 'assistant_prefill': assistant_prefill})
        if self._scripted_responses:
            return self._scripted_responses.popleft()
        return self._default_response

    async def train_lora(self, train_data_path: str, adapter_path: str) -> None:
        self.train_calls.append({'train_data_path': train_data_path, 'adapter_path': adapter_path})
        if self._train_should_raise is not None:
            raise self._train_should_raise

    def script_responses(self, responses: list[str]) -> None:
        self._scripted_responses.extend(responses)

    def set_default_response(self, response: str) -> None:
        self._default_response = response

    def fail_training_with(self, exc: Exception) -> None:
        self._train_should_raise = exc
