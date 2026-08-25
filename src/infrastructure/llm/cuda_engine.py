__all__ = ["CUDAInferenceEngine"]

import asyncio
import dataclasses
import json
import time
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np
import torch
import torch.nn as nn
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    GenerationConfig
)
from peft import (
    get_peft_model,
    LoraConfig,
    PeftModel,
    TaskType
)

import constants
from infrastructure.llm import IInferenceEngine

MODEL_PATHS: dict[constants.AvailableModel, str] = {
    constants.AvailableModel.QWEN_3_5_9B: "Qwen/Qwen3.5-9B",
    constants.AvailableModel.QWEN_3_5_4B: "Qwen/Qwen3.5-4B",
    constants.AvailableModel.QWEN_2_5_3B: "Qwen/Qwen2.5-3B-Instruct",
    constants.AvailableModel.QWEN_2_5_1_5B: "Qwen/Qwen2.5-1.5B-Instruct",
    constants.AvailableModel.LLAMA_3_2_3B: "meta-llama/Llama-3.2-3B-Instruct",
}

StepFn = Callable[[np.ndarray, np.ndarray, np.ndarray], float]
BatchSpec = tuple[np.ndarray, np.ndarray, np.ndarray]
BucketPlan = dict[int, list[BatchSpec]]


@dataclasses.dataclass
class _TrainExample:
    tokens: list[int]
    prefix_len: int


class CUDAInferenceEngine(IInferenceEngine):
    @dataclasses.dataclass(order=True)
    class _GenerationRequest:
        priority: int
        timestamp: float
        future: asyncio.Future = dataclasses.field(compare=False)
        kwargs: dict[str, Any] = dataclasses.field(compare=False)

    _LORA_PARAMETERS: dict[str, Any] = {
        "r": 8,
        "lora_alpha": 16.0,
        "lora_dropout": 0.1,
    }
    _BUCKET_CANDIDATES: list[int] = [128, 256, 512, 1024, 2048, 4096]
    _SNAPSHOT_EVERY_N_BATCHES: int = 1

    def __init__(
            self,
            base_model: constants.AvailableModel,
    ):
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is required but not available.")
        self.device = torch.device("cuda")

        self._base_model: constants.AvailableModel = base_model
        self._model: Optional[Any] = None
        self._tokenizer: Optional[Any] = None
        self._active_lora_path: Optional[str] = None
        self._lora_wrapped: bool = False
        self._frozen_system_prompt: Optional[str] = None
        self._frozen_cache_state: Optional[tuple] = None
        self._queue: Optional[asyncio.PriorityQueue] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._gpu_lock: asyncio.Lock = asyncio.Lock()
        self._is_training: bool = False
        self._active_training_adapter_path: Optional[str] = None

        self._load_base_model(base_model)

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
        self._ensure_worker_started()
        future: asyncio.Future = self._submit_generation_request(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            lora_path=lora_path,
            max_tokens=max_tokens,
            temp=temp,
            priority=priority,
            assistant_prefill=assistant_prefill,
        )
        return await future

    async def evaluate_loss(
            self,
            jsonl_path: str,
            adapter_path: Optional[str],
    ) -> dict[str, float]:
        self._ensure_worker_started()
        future: asyncio.Future = asyncio.get_running_loop().create_future()

        async def _run() -> None:
            async with self._gpu_lock:
                try:
                    result: dict[str, float] = await asyncio.to_thread(
                        self._sync_evaluate_loss, jsonl_path, adapter_path,
                    )
                    self._set_future_result(future, result)
                except Exception as e:
                    self._set_future_exception(future, e)

        asyncio.create_task(_run())
        return await future

    def _sync_evaluate_loss(
            self,
            jsonl_path: str,
            adapter_path: Optional[str],
    ) -> dict[str, float]:
        snapshot: Optional[dict[str, torch.Tensor]] = None
        if self._is_training:
            if adapter_path != self._active_training_adapter_path:
                snapshot = self._snapshot_training_lora_weights()
                self._apply_adapter_for_inference(adapter_path)
            self._invalidate_frozen_cache()
        else:
            self._switch_lora_if_needed(adapter_path)

        try:
            self._model.eval()
            examples: list[_TrainExample] = self._load_train_examples(Path(jsonl_path))
            if not examples:
                return {
                    "avg_loss": 0.0,
                    "perplexity": float("nan"),
                    "n_samples": 0,
                    "n_tokens": 0,
                }

            total_loss: float = 0.0
            total_tokens: float = 0.0
            n_samples: int = 0

            with torch.no_grad():
                for example in examples:
                    inputs_np: np.ndarray = np.array(example.tokens[:-1], dtype=np.int64)[None]
                    targets_np: np.ndarray = np.array(example.tokens[1:], dtype=np.int64)[None]
                    seq_len: int = len(example.tokens) - 1
                    mask_np: np.ndarray = np.zeros((1, seq_len), dtype=np.float32)
                    response_start: int = max(0, example.prefix_len - 1)
                    if response_start >= seq_len:
                        continue
                    mask_np[0, response_start:seq_len] = 1.0

                    inputs_b: torch.Tensor = torch.tensor(inputs_np, device=self.device)
                    targets_b: torch.Tensor = torch.tensor(targets_np, device=self.device)
                    mask_b: torch.Tensor = torch.tensor(mask_np, device=self.device)

                    outputs = self._model(input_ids=inputs_b)
                    logits = outputs.logits.float()

                    ce = nn.functional.cross_entropy(
                        logits.view(-1, logits.size(-1)),
                        targets_b.view(-1),
                        reduction="none"
                    )
                    ce = ce.view(targets_b.size())
                    masked = ce * mask_b

                    token_count: float = float(mask_b.sum().item())
                    if token_count <= 0:
                        continue

                    sample_loss: float = float(masked.sum().item())
                    total_loss += sample_loss
                    total_tokens += token_count
                    n_samples += 1

            avg_loss: float = total_loss / total_tokens if total_tokens > 0 else 0.0
            perplexity: float = float(np.exp(avg_loss)) if avg_loss < 50.0 else float("inf")
            return {
                "avg_loss": avg_loss,
                "perplexity": perplexity,
                "n_samples": n_samples,
                "n_tokens": int(total_tokens),
            }
        finally:
            if snapshot is not None:
                self._restore_training_lora_weights(snapshot)
                self._invalidate_frozen_cache()
            self._safe_clear_cache()

    async def train_lora(
            self,
            train_data_path: str,
            adapter_path: str,
    ) -> None:
        if self._is_training:
            raise RuntimeError("Training is already in progress")

        self._ensure_worker_started()
        self._is_training = True
        self._active_training_adapter_path = adapter_path

        try:
            bucket_plan: BucketPlan = await asyncio.to_thread(
                self._prepare_dataset_buckets,
                Path(train_data_path),
            )

            if not bucket_plan:
                print("No training batches available.")
                return

            self._log_bucket_summary(bucket_plan)

            async with self._gpu_lock:
                step_fn: StepFn = await asyncio.to_thread(self._setup_model_for_training)

            await self._run_training_with_yielding(
                bucket_plan=bucket_plan,
                step_fn=step_fn,
                adapter_path=adapter_path,
            )

            async with self._gpu_lock:
                await asyncio.to_thread(self._save_adapters, adapter_path)
            self._active_lora_path = adapter_path
        finally:
            async with self._gpu_lock:
                await asyncio.to_thread(self._cleanup_after_training)
                self._is_training = False
                self._active_training_adapter_path = None
            self._invalidate_frozen_cache()

    def _load_base_model(
            self,
            base_model: constants.AvailableModel,
    ) -> None:
        base_model_path: Optional[str] = MODEL_PATHS.get(base_model)
        if base_model_path is None:
            raise ValueError(f"Unsupported model: {base_model}")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=False,
        )

        self._tokenizer = AutoTokenizer.from_pretrained(base_model_path)
        if self._tokenizer.pad_token_id is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        self._model = AutoModelForCausalLM.from_pretrained(
            base_model_path,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.float16
        )
        self._model.eval()
        self._lora_wrapped = False
        self._active_lora_path = None

    def _ensure_worker_started(self) -> None:
        if self._queue is not None:
            return

        self._queue = asyncio.PriorityQueue()
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def _worker_loop(self) -> None:
        while True:
            request: CUDAInferenceEngine._GenerationRequest = await self._queue.get()
            await self._process_generation_request(request)

    async def _process_generation_request(
            self,
            request: "CUDAInferenceEngine._GenerationRequest",
    ) -> None:
        async with self._gpu_lock:
            try:
                result: str = await asyncio.to_thread(
                    self._sync_generate,
                    **request.kwargs,
                )
                self._set_future_result(request.future, result)
            except Exception as e:
                self._set_future_exception(request.future, e)
            finally:
                self._queue.task_done()

    def _submit_generation_request(
            self,
            system_prompt: str,
            user_prompt: str,
            lora_path: Optional[str],
            max_tokens: int,
            temp: float,
            priority: int,
            assistant_prefill: str,
    ) -> asyncio.Future:
        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        kwargs: dict[str, Any] = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "lora_path": lora_path,
            "max_tokens": max_tokens,
            "temp": temp,
            "assistant_prefill": assistant_prefill,
        }
        request = self._GenerationRequest(
            priority=priority,
            timestamp=time.monotonic(),
            future=future,
            kwargs=kwargs,
        )
        self._queue.put_nowait(request)
        return future

    @staticmethod
    def _set_future_result(
            future: asyncio.Future,
            result: Any,
    ) -> None:
        if not future.done():
            future.set_result(result)

    @staticmethod
    def _set_future_exception(
            future: asyncio.Future,
            exception: Exception,
    ) -> None:
        if not future.done():
            future.set_exception(exception)

    def _sync_generate(
            self,
            system_prompt: str,
            user_prompt: str,
            lora_path: Optional[str],
            max_tokens: int,
            temp: float,
            assistant_prefill: str,
    ) -> str:
        snapshot: Optional[dict[str, torch.Tensor]] = None
        if self._is_training:
            if lora_path != self._active_training_adapter_path:
                snapshot = self._snapshot_training_lora_weights()
                self._apply_adapter_for_inference(lora_path)
            self._invalidate_frozen_cache()
        else:
            self._switch_lora_if_needed(lora_path)

        try:
            sys_tokens: list[int] = self._tokenize_system_prompt(system_prompt)
            past_key_values = self._get_frozen_cache(system_prompt, sys_tokens)
            delta_tokens: list[int] = self._build_delta_tokens(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                assistant_prefill=assistant_prefill,
                sys_tokens_count=len(sys_tokens),
            )

            input_ids = torch.tensor([delta_tokens], device=self.device)

            gen_config = GenerationConfig(
                max_new_tokens=max_tokens,
                temperature=temp,
                top_p=constants.IMITATION_TOP_P,
                repetition_penalty=constants.IMITATION_REPETITION_PENALTY,
                do_sample=True,
            )

            with torch.no_grad():
                output_ids = self._model.generate(
                    input_ids=input_ids,
                    past_key_values=past_key_values,
                    generation_config=gen_config,
                    use_cache=True
                )

            new_tokens = output_ids[0][input_ids.shape[1]:]
            return self._tokenizer.decode(new_tokens, skip_special_tokens=True)
        finally:
            if snapshot is not None:
                self._restore_training_lora_weights(snapshot)
                self._invalidate_frozen_cache()

    def _switch_lora_if_needed(
            self,
            lora_path: Optional[str],
    ) -> None:
        if lora_path == self._active_lora_path:
            return

        self._apply_adapter(lora_path)
        self._active_lora_path = lora_path
        self._invalidate_frozen_cache()

    def _apply_adapter(
            self,
            lora_path: Optional[str],
    ) -> None:
        if lora_path is None:
            if isinstance(self._model, PeftModel):
                self._model.disable_adapter_layers()
            return

        adapter_file = Path(lora_path)
        if not adapter_file.exists():
            raise FileNotFoundError(f"Adapter weights not found: {adapter_file}")

        adapter_name = str(adapter_file.resolve())
        if not isinstance(self._model, PeftModel):
            self._model = PeftModel.from_pretrained(
                self._model,
                lora_path,
                adapter_name=adapter_name,
            )
            self._lora_wrapped = True
        else:
            self._model.enable_adapter_layers()
            if adapter_name not in self._model.peft_config:
                self._model.load_adapter(lora_path, adapter_name=adapter_name)
            self._model.set_adapter(adapter_name)

        self._model.eval()

    def _zero_lora_adapter_weights(self) -> None:
        if isinstance(self._model, PeftModel):
            self._model.disable_adapter_layers()

    def _snapshot_training_lora_weights(self) -> dict[str, torch.Tensor]:
        if not isinstance(self._model, PeftModel):
            return {}
        return {k: v.cpu().clone() for k, v in self._model.state_dict().items() if "lora" in k}

    def _restore_training_lora_weights(
            self,
            snapshot: dict[str, torch.Tensor],
    ) -> None:
        if isinstance(self._model, PeftModel) and snapshot:
            self._model.load_state_dict(snapshot, strict=False)

    def _apply_adapter_for_inference(
            self,
            lora_path: Optional[str],
    ) -> None:
        self._apply_adapter(lora_path)

    def _zero_lora_weights(self) -> None:
        if isinstance(self._model, PeftModel):
            self._model.disable_adapter_layers()

    def _invalidate_frozen_cache(self) -> None:
        self._frozen_system_prompt = None
        self._frozen_cache_state = None

    def _tokenize_system_prompt(
            self,
            system_prompt: str,
    ) -> list[int]:
        sys_text: str = self._format_system_prompt_text(system_prompt)
        return self._tokenizer.encode(sys_text)

    def _format_system_prompt_text(
            self,
            system_prompt: str,
    ) -> str:
        if self._base_model.is_qwen():
            return f"<|im_start|>system\n{system_prompt}<|im_end|>\n"

        sys_messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]
        return self._tokenizer.apply_chat_template(
            sys_messages,
            tokenize=False,
            add_generation_prompt=False,
        )

    def _build_delta_tokens(
            self,
            system_prompt: str,
            user_prompt: str,
            assistant_prefill: str,
            sys_tokens_count: int,
    ) -> list[int]:
        full_messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        full_text: str = self._tokenizer.apply_chat_template(
            full_messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        full_text += assistant_prefill
        full_tokens: list[int] = self._tokenizer.encode(full_text)
        return full_tokens[sys_tokens_count:]

    def _get_frozen_cache(
            self,
            system_prompt: str,
            sys_tokens: list[int],
    ) -> Optional[tuple]:
        if not self._is_frozen_cache_valid(system_prompt):
            self._compute_and_store_frozen_cache(system_prompt, sys_tokens)

        return self._clone_frozen_cache()

    def _is_frozen_cache_valid(
            self,
            system_prompt: str,
    ) -> bool:
        return (
                self._frozen_system_prompt == system_prompt
                and self._frozen_cache_state is not None
        )

    def _clone_frozen_cache(self) -> Optional[tuple]:
        if not self._frozen_cache_state:
            return None
        return tuple(
            tuple(t.clone() for t in layer)
            for layer in self._frozen_cache_state
        )

    def _compute_and_store_frozen_cache(
            self,
            system_prompt: str,
            sys_tokens: list[int],
    ) -> None:
        input_ids = torch.tensor([sys_tokens], device=self.device)
        with torch.no_grad():
            outputs = self._model(input_ids, use_cache=True)

        self._frozen_cache_state = tuple(
            tuple(t.detach().clone() for t in layer)
            for layer in outputs.past_key_values
        )
        self._frozen_system_prompt = system_prompt

    def _setup_model_for_training(self) -> StepFn:
        self._safe_clear_cache()
        self._prepare_model_for_training()
        optimizer = torch.optim.AdamW(self._model.parameters(), lr=constants.LORA_LR)
        step_fn: StepFn = self._build_step_fn(optimizer)
        self._safe_reset_peak_memory()
        return step_fn

    def _cleanup_after_training(self) -> None:
        self._model.eval()
        self._safe_clear_cache()

    def _prepare_model_for_training(self) -> None:
        if self._lora_wrapped:
            self._load_base_model(self._base_model)
            self._invalidate_frozen_cache()

        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            inference_mode=False,
            r=self._LORA_PARAMETERS["r"],
            lora_alpha=self._LORA_PARAMETERS["lora_alpha"],
            lora_dropout=self._LORA_PARAMETERS["lora_dropout"],
            target_modules=constants.LORA_LAYERS
        )

        self._model = get_peft_model(self._model, lora_config)
        self._model.train()
        self._lora_wrapped = True
        self._enable_gradient_checkpointing()

    def _enable_gradient_checkpointing(self) -> None:
        if hasattr(self._model, "gradient_checkpointing_enable"):
            self._model.gradient_checkpointing_enable()

    def _build_step_fn(
            self,
            optimizer: torch.optim.Optimizer,
    ) -> StepFn:
        def step_with_eval(
                inputs_np: np.ndarray,
                targets_np: np.ndarray,
                mask_np: np.ndarray,
        ) -> float:
            optimizer.zero_grad()

            inputs_b = torch.tensor(inputs_np, dtype=torch.long, device=self.device)
            targets_b = torch.tensor(targets_np, dtype=torch.long, device=self.device)
            mask_b = torch.tensor(mask_np, dtype=torch.float32, device=self.device)

            outputs = self._model(input_ids=inputs_b)
            logits = outputs.logits.float()

            ce = nn.functional.cross_entropy(
                logits.view(-1, logits.size(-1)),
                targets_b.view(-1),
                reduction="none"
            )
            ce = ce.view(targets_b.size())
            loss = (ce * mask_b).sum() / torch.clamp(mask_b.sum(), min=1.0)

            loss.backward()
            optimizer.step()

            return loss.item()

        return step_with_eval

    async def _run_training_with_yielding(
            self,
            bucket_plan: BucketPlan,
            step_fn: StepFn,
            adapter_path: str,
    ) -> None:
        total_batches: int = sum(len(specs) for specs in bucket_plan.values())
        n_epochs: int = self._adaptive_epochs(updates_per_epoch=total_batches)
        total_updates: int = n_epochs * total_batches
        print(
            f"Starting training: {n_epochs} epoch(s) x {total_batches} batches = "
            f"{total_updates} updates (target {constants.LORA_TARGET_UPDATES})"
        )

        for epoch in range(n_epochs):
            await self._run_epoch_with_yielding(
                epoch=epoch,
                n_epochs=n_epochs,
                bucket_plan=bucket_plan,
                step_fn=step_fn,
                total_batches=total_batches,
                adapter_path=adapter_path,
            )

    @staticmethod
    def _adaptive_epochs(updates_per_epoch: int) -> int:
        if updates_per_epoch <= 0:
            return constants.LORA_MIN_EPOCHS

        raw: int = constants.LORA_TARGET_UPDATES // updates_per_epoch
        return max(
            constants.LORA_MIN_EPOCHS,
            min(constants.LORA_MAX_EPOCHS, raw),
        )

    async def _run_epoch_with_yielding(
            self,
            epoch: int,
            n_epochs: int,
            bucket_plan: BucketPlan,
            step_fn: StepFn,
            total_batches: int,
            adapter_path: str,
    ) -> None:
        epoch_loss: float = 0.0
        epoch_time: float = 0.0
        seen: int = 0

        for bucket_size, batch_specs in bucket_plan.items():
            for spec in batch_specs:
                seen += 1

                async with self._gpu_lock:
                    loss_val, elapsed = await asyncio.to_thread(
                        self._execute_training_step, spec, step_fn,
                    )
                    self._invalidate_frozen_cache()
                    self._safe_clear_cache()
                    if seen % self._SNAPSHOT_EVERY_N_BATCHES == 0:
                        await asyncio.to_thread(self._save_adapters, adapter_path)

                epoch_loss += loss_val
                epoch_time += elapsed
                self._log_batch_progress(
                    epoch=epoch,
                    n_epochs=n_epochs,
                    bucket_size=bucket_size,
                    seen=seen,
                    total_batches=total_batches,
                    loss_val=loss_val,
                    elapsed=elapsed,
                )
                await asyncio.sleep(0)

        self._log_epoch_summary(
            epoch=epoch,
            epoch_loss=epoch_loss,
            epoch_time=epoch_time,
            seen=seen,
        )

    @staticmethod
    def _execute_training_step(
            spec: BatchSpec,
            step_fn: StepFn,
    ) -> tuple[float, float]:
        inputs_np, targets_np, mask_np = spec

        start: float = time.perf_counter()
        loss_val: float = step_fn(inputs_np, targets_np, mask_np)
        elapsed: float = time.perf_counter() - start

        return loss_val, elapsed

    def _save_adapters(
            self,
            adapter_path: str,
    ) -> None:
        if isinstance(self._model, PeftModel):
            self._model.save_pretrained(adapter_path)
            print("Training successfully completed. Adapters saved.")

    def _log_batch_progress(
            self,
            epoch: int,
            n_epochs: int,
            bucket_size: int,
            seen: int,
            total_batches: int,
            loss_val: float,
            elapsed: float,
    ) -> None:
        peak_gb: float = self._safe_get_peak_memory_gb()
        print(
            f"Epoch {epoch + 1}/{n_epochs} | "
            f"Bucket {bucket_size} | Batch {seen}/{total_batches} | "
            f"Loss: {loss_val:.4f} | Step: {elapsed:.2f}s | Peak: {peak_gb:.2f}GB"
        )

    @staticmethod
    def _log_epoch_summary(
            epoch: int,
            epoch_loss: float,
            epoch_time: float,
            seen: int,
    ) -> None:
        if seen == 0:
            return
        avg_loss: float = epoch_loss / seen
        avg_time: float = epoch_time / seen
        print(
            f"--- Epoch {epoch + 1} completed | "
            f"Avg Loss: {avg_loss:.4f} | Avg step: {avg_time:.2f}s ---"
        )

    @staticmethod
    def _log_bucket_summary(
            bucket_plan: BucketPlan,
    ) -> None:
        total_batches: int = sum(len(specs) for specs in bucket_plan.values())
        bucket_counts: dict[int, int] = {
            size: len(specs) for size, specs in bucket_plan.items()
        }
        print(
            f"Prepared {total_batches} batches across {len(bucket_plan)} buckets: "
            f"{bucket_counts}"
        )

    @staticmethod
    def _safe_clear_cache() -> None:
        torch.cuda.empty_cache()

    @staticmethod
    def _safe_reset_peak_memory() -> None:
        torch.cuda.reset_peak_memory_stats()

    @staticmethod
    def _safe_get_peak_memory_gb() -> float:
        return torch.cuda.max_memory_allocated() / (1024 ** 3)

    def _prepare_dataset_buckets(
            self,
            train_file: Path,
    ) -> BucketPlan:
        all_examples: list[_TrainExample] = self._load_train_examples(train_file)
        if not all_examples:
            return {}

        pad_id: int = self._get_pad_token_id()
        bucket_sizes: list[int] = self._compute_bucket_sizes(constants.LORA_MAX_SEQ_LENGTH)
        bucketed: dict[int, list[_TrainExample]] = self._assign_to_buckets(
            all_examples=all_examples,
            bucket_sizes=bucket_sizes,
        )

        result: BucketPlan = {}
        for bucket_size, examples in bucketed.items():
            batches: list[BatchSpec] = self._build_batches_for_bucket(
                bucket_size=bucket_size,
                examples=examples,
                pad_id=pad_id,
            )
            if batches:
                result[bucket_size] = batches

        return result

    def _load_train_examples(
            self,
            train_file: Path,
    ) -> list[_TrainExample]:
        with open(train_file, "r", encoding="utf-8") as f:
            lines: list[str] = f.readlines()

        max_seq: int = constants.LORA_MAX_SEQ_LENGTH
        examples: list[_TrainExample] = []
        for line in lines:
            example: Optional[_TrainExample] = self._tokenize_train_entry(line, max_seq)
            if example is not None:
                examples.append(example)

        return examples

    def _tokenize_train_entry(
            self,
            jsonl_line: str,
            max_seq: int,
    ) -> Optional[_TrainExample]:
        data: dict[str, Any] = json.loads(jsonl_line)
        messages: list[dict[str, str]] = data["messages"]

        prompt_text: str = self._tokenizer.apply_chat_template(
            messages[:-1],
            tokenize=False,
            add_generation_prompt=True,
        )
        prompt_tokens: list[int] = self._tokenizer.encode(prompt_text)
        prefix_len: int = len(prompt_tokens)

        full_text: str = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
        full_tokens: list[int] = self._tokenizer.encode(full_text)
        if len(full_tokens) > max_seq:
            full_tokens = full_tokens[:max_seq]

        if prefix_len >= len(full_tokens) or len(full_tokens) < 2:
            return None

        return _TrainExample(tokens=full_tokens, prefix_len=prefix_len)

    def _get_pad_token_id(self) -> int:
        pad_id: Optional[int] = getattr(self._tokenizer, "pad_token_id", None)
        if pad_id is not None:
            return pad_id
        eos_id: Optional[int] = getattr(self._tokenizer, "eos_token_id", None)
        return eos_id if eos_id is not None else 0

    @classmethod
    def _compute_bucket_sizes(
            cls,
            max_seq: int,
    ) -> list[int]:
        bucket_sizes: list[int] = [b for b in cls._BUCKET_CANDIDATES if b <= max_seq]
        if not bucket_sizes or bucket_sizes[-1] < max_seq:
            bucket_sizes.append(max_seq)
        return sorted(set(bucket_sizes))

    @staticmethod
    def _assign_to_buckets(
            all_examples: list[_TrainExample],
            bucket_sizes: list[int],
    ) -> dict[int, list[_TrainExample]]:
        bucketed: dict[int, list[_TrainExample]] = {b: [] for b in bucket_sizes}
        largest_bucket: int = bucket_sizes[-1]
        for example in all_examples:
            placed: bool = False
            for bucket_size in bucket_sizes:
                if len(example.tokens) <= bucket_size:
                    bucketed[bucket_size].append(example)
                    placed = True
                    break
            if not placed:
                truncated_tokens: list[int] = example.tokens[:largest_bucket]
                if example.prefix_len >= len(truncated_tokens):
                    continue
                bucketed[largest_bucket].append(
                    _TrainExample(tokens=truncated_tokens, prefix_len=example.prefix_len)
                )
        return bucketed

    def _build_batches_for_bucket(
            self,
            bucket_size: int,
            examples: list[_TrainExample],
            pad_id: int,
    ) -> list[BatchSpec]:
        if not examples:
            return []

        batch_size: int = constants.LORA_BATCH_SIZE
        batches: list[BatchSpec] = []
        for i in range(0, len(examples), batch_size):
            batch_examples: list[_TrainExample] = examples[i:i + batch_size]
            if len(batch_examples) < batch_size:
                continue
            batches.append(self._build_single_batch(
                batch_examples=batch_examples,
                bucket_size=bucket_size,
                pad_id=pad_id,
            ))
        return batches

    @classmethod
    def _build_single_batch(
            cls,
            batch_examples: list[_TrainExample],
            bucket_size: int,
            pad_id: int,
    ) -> BatchSpec:
        seq_len: int = bucket_size - 1
        batch_inputs: list[list[int]] = []
        batch_targets: list[list[int]] = []
        batch_mask: list[list[float]] = []

        for example in batch_examples:
            inputs, targets, mask = cls._build_single_example(
                example=example,
                bucket_size=bucket_size,
                seq_len=seq_len,
                pad_id=pad_id,
            )
            batch_inputs.append(inputs)
            batch_targets.append(targets)
            batch_mask.append(mask)

        return (
            np.array(batch_inputs, dtype=np.int32),
            np.array(batch_targets, dtype=np.int32),
            np.array(batch_mask, dtype=np.float32),
        )

    @staticmethod
    def _build_single_example(
            example: _TrainExample,
            bucket_size: int,
            seq_len: int,
            pad_id: int,
    ) -> tuple[list[int], list[int], list[float]]:
        tokens: list[int] = example.tokens
        seq: list[int] = list(tokens[:bucket_size])
        pad_needed: int = bucket_size - len(seq)
        if pad_needed > 0:
            seq = seq + [pad_id] * pad_needed

        inputs: list[int] = seq[:-1]
        targets: list[int] = seq[1:]

        response_start: int = max(0, example.prefix_len - 1)
        response_end: int = max(0, min(len(tokens), bucket_size) - 1)

        mask: list[float] = [0.0] * seq_len
        for i in range(response_start, response_end):
            mask[i] = 1.0
        return inputs, targets, mask
