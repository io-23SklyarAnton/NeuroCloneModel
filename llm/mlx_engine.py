import asyncio
import dataclasses
import json
import time
from functools import partial
from pathlib import Path
from typing import Any, Callable, Optional

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import mlx.utils as mx_utils
import numpy as np
from mlx_lm import generate, load
from mlx_lm.models.cache import make_prompt_cache
from mlx_lm.sample_utils import make_sampler
from mlx_lm.tuner.utils import linear_to_lora_layers

import constants
from llm.i_inference_engine import IInferenceEngine


MODEL_PATHS: dict[constants.AvailableModel, str] = {
    constants.AvailableModel.QWEN_3_5_9B: "mlx-community/Qwen3.5-9B-OptiQ-4bit",
    constants.AvailableModel.QWEN_3_5_4B: "mlx-community/Qwen3.5-4B-4bit",
    constants.AvailableModel.QWEN_2_5_3B: "mlx-community/Qwen2.5-3B-Instruct-4bit",
    constants.AvailableModel.QWEN_2_5_1_5B: "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
    constants.AvailableModel.LLAMA_3_2_3B: "mlx-community/Llama-3.2-3B-Instruct-4bit",
}


StepFn = Callable[[mx.array, mx.array, mx.array], float]
BatchSpec = tuple[np.ndarray, np.ndarray, np.ndarray]
BucketPlan = dict[int, list[BatchSpec]]


@dataclasses.dataclass
class _TrainExample:
    tokens: list[int]
    prefix_len: int


class MLXInferenceEngine(IInferenceEngine):
    @dataclasses.dataclass(order=True)
    class _GenerationRequest:
        priority: int
        timestamp: float
        future: asyncio.Future = dataclasses.field(compare=False)
        kwargs: dict[str, Any] = dataclasses.field(compare=False)

    _LORA_PARAMETERS: dict[str, Any] = {
        "rank": 8,
        "alpha": 16.0,
        "scale": 2.0,
        "dropout": 0.0,
    }
    _BUCKET_CANDIDATES: list[int] = [128, 256, 512, 1024, 2048, 4096]
    _ADAPTER_FILENAME: str = "adapters.safetensors"
    _TRAIN_FILENAME: str = "train.jsonl"

    def __init__(
            self,
            base_model: constants.AvailableModel,
    ):
        self._base_model: constants.AvailableModel = base_model
        self._model: Optional[nn.Module] = None
        self._tokenizer: Any = None
        self._active_lora_path: Optional[str] = None
        self._frozen_system_prompt: Optional[str] = None
        self._frozen_cache_state: Optional[list[list[mx.array]]] = None
        self._queue: Optional[asyncio.PriorityQueue] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._gpu_lock: asyncio.Lock = asyncio.Lock()
        self._is_training: bool = False

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

    async def train_lora(
            self,
            data_dir: str,
            adapter_path: str,
    ) -> None:
        if self._is_training:
            raise RuntimeError("Training is already in progress")

        self._ensure_worker_started()
        self._is_training = True

        try:
            async with self._gpu_lock:
                await asyncio.to_thread(
                    self._sync_train_lora,
                    data_dir,
                    adapter_path,
                )
        finally:
            self._is_training = False
            self._invalidate_frozen_cache()

    def _load_base_model(
            self,
            base_model: constants.AvailableModel,
    ) -> None:
        base_model_path: Optional[str] = MODEL_PATHS.get(base_model)
        if base_model_path is None:
            raise ValueError(f"Unsupported model: {base_model}")

        self._model, self._tokenizer = load(base_model_path)

    def _ensure_worker_started(self) -> None:
        if self._queue is not None:
            return

        self._queue = asyncio.PriorityQueue()
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def _worker_loop(self) -> None:
        while True:
            request: MLXInferenceEngine._GenerationRequest = await self._queue.get()
            await self._process_generation_request(request)

    async def _process_generation_request(
            self,
            request: "MLXInferenceEngine._GenerationRequest",
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
        self._switch_lora_if_needed(lora_path)

        sys_tokens: list[int] = self._tokenize_system_prompt(system_prompt)
        prompt_cache: list[Any] = self._get_frozen_cache(system_prompt, sys_tokens)
        delta_tokens: list[int] = self._build_delta_tokens(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            assistant_prefill=assistant_prefill,
            sys_tokens_count=len(sys_tokens),
        )

        return generate(
            self._model,
            self._tokenizer,
            prompt=delta_tokens,
            prompt_cache=prompt_cache,
            max_tokens=max_tokens,
            sampler=make_sampler(temp=temp),
            verbose=False,
        )

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
            self._load_base_model(self._base_model)
            return

        adapter_dir = Path(lora_path)
        adapter_file = adapter_dir / self._ADAPTER_FILENAME
        if not adapter_file.exists():
            raise FileNotFoundError(f"Adapter weights not found: {adapter_file}")

        linear_to_lora_layers(self._model, constants.LORA_LAYERS, self._LORA_PARAMETERS)
        weights = dict(mx.load(str(adapter_file)))
        self._model.load_weights(list(weights.items()), strict=False)
        mx.eval(self._model.parameters())
        self._model.eval()

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
    ) -> list[Any]:
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

    def _clone_frozen_cache(self) -> list[Any]:
        new_cache: list[Any] = make_prompt_cache(self._model)
        for i, layer_cache in enumerate(new_cache):
            layer_cache.state = [mx.add(s, 0) for s in self._frozen_cache_state[i]]
        return new_cache

    def _compute_and_store_frozen_cache(
            self,
            system_prompt: str,
            sys_tokens: list[int],
    ) -> None:
        cache: list[Any] = make_prompt_cache(self._model)
        prompt_array: mx.array = mx.array(sys_tokens)[None]
        _ = self._model(prompt_array, cache=cache)
        mx.eval([c.state for c in cache])

        self._frozen_cache_state = [
            [mx.add(s, 0) for s in c.state]
            for c in cache
        ]
        for state_list in self._frozen_cache_state:
            mx.eval(state_list)

        self._frozen_system_prompt = system_prompt

    def _sync_train_lora(
            self,
            data_dir: str,
            adapter_path: str,
    ) -> None:
        self._safe_clear_cache()
        self._prepare_model_for_training()

        optimizer: optim.Adam = self._create_lora_optimizer()
        bucket_plan: BucketPlan = self._prepare_dataset_buckets(Path(data_dir))

        if not bucket_plan:
            print("No training batches available.")
            self._model.eval()
            return

        self._log_bucket_summary(bucket_plan)

        step_fn: StepFn = self._build_step_fn(optimizer)
        self._safe_reset_peak_memory()

        try:
            self._run_training_epochs(
                bucket_plan=bucket_plan,
                step_fn=step_fn,
            )
            self._save_adapters(adapter_path)
        finally:
            self._model.eval()
            self._safe_clear_cache()

    def _prepare_model_for_training(self) -> None:
        self._model.train()
        self._model.freeze()
        linear_to_lora_layers(
            self._model,
            constants.LORA_LAYERS,
            self._LORA_PARAMETERS,
        )
        self._enable_gradient_checkpointing()
        mx.eval(self._model.parameters())

    def _enable_gradient_checkpointing(self) -> None:
        if not hasattr(self._model, "layers") or not self._model.layers:
            return

        try:
            self._wrap_layer_with_checkpointing(self._model.layers[0])
            print("Gradient checkpointing enabled.")
        except Exception as e:
            print(f"Could not enable gradient checkpointing: {e}")

    @staticmethod
    def _wrap_layer_with_checkpointing(
            layer: nn.Module,
    ) -> None:
        original_call = type(layer).__call__

        def checkpointed_call(model, *args, **kwargs):
            def inner(params, *args, **kwargs):
                model.update(params)
                return original_call(model, *args, **kwargs)
            return mx.checkpoint(inner)(
                model.trainable_parameters(),
                *args,
                **kwargs,
            )

        type(layer).__call__ = checkpointed_call

    def _create_lora_optimizer(self) -> optim.Adam:
        optimizer: optim.Adam = optim.Adam(learning_rate=constants.LORA_LR)
        optimizer.init(self._model.trainable_parameters())
        mx.eval(optimizer.state)
        return optimizer

    def _build_step_fn(
            self,
            optimizer: optim.Adam,
    ) -> StepFn:
        loss_and_grad_fn = nn.value_and_grad(self._model, self._loss_fn)
        state: list[Any] = [self._model.state, optimizer.state, mx.random.state]

        @partial(mx.compile, inputs=state, outputs=state)
        def compiled_step(inputs_b, targets_b, mask_b):
            loss, grads = loss_and_grad_fn(self._model, inputs_b, targets_b, mask_b)
            optimizer.update(self._model, grads)
            return loss

        def step_with_eval(
                inputs_b: mx.array,
                targets_b: mx.array,
                mask_b: mx.array,
        ) -> float:
            loss: mx.array = compiled_step(inputs_b, targets_b, mask_b)
            mx.eval(state, loss)
            return float(loss.item())

        return step_with_eval

    @staticmethod
    def _loss_fn(
            model: nn.Module,
            inputs_b: mx.array,
            targets_b: mx.array,
            mask_b: mx.array,
    ) -> mx.array:
        logits: mx.array = model(inputs_b).astype(mx.float32)
        ce: mx.array = nn.losses.cross_entropy(logits, targets_b, reduction="none")
        return (ce * mask_b).sum() / mx.maximum(mask_b.sum(), mx.array(1.0))

    def _run_training_epochs(
            self,
            bucket_plan: BucketPlan,
            step_fn: StepFn,
    ) -> None:
        total_batches: int = sum(len(specs) for specs in bucket_plan.values())
        print(f"Starting training for {constants.LORA_ITERS} epochs...")

        for epoch in range(constants.LORA_ITERS):
            self._run_epoch(
                epoch=epoch,
                bucket_plan=bucket_plan,
                step_fn=step_fn,
                total_batches=total_batches,
            )

    def _run_epoch(
            self,
            epoch: int,
            bucket_plan: BucketPlan,
            step_fn: StepFn,
            total_batches: int,
    ) -> None:
        epoch_loss: float = 0.0
        epoch_time: float = 0.0
        seen: int = 0

        for bucket_size, batch_specs in bucket_plan.items():
            for spec in batch_specs:
                seen += 1
                loss_val, elapsed = self._execute_training_step(spec, step_fn)
                epoch_loss += loss_val
                epoch_time += elapsed
                self._log_batch_progress(
                    epoch=epoch,
                    bucket_size=bucket_size,
                    seen=seen,
                    total_batches=total_batches,
                    loss_val=loss_val,
                    elapsed=elapsed,
                )
                self._safe_clear_cache()

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
        inputs_b: mx.array = mx.array(inputs_np)
        targets_b: mx.array = mx.array(targets_np)
        mask_b: mx.array = mx.array(mask_np)

        start: float = time.perf_counter()
        loss_val: float = step_fn(inputs_b, targets_b, mask_b)
        elapsed: float = time.perf_counter() - start

        return loss_val, elapsed

    def _save_adapters(
            self,
            adapter_path: str,
    ) -> None:
        out_path: Path = Path(adapter_path)
        out_path.mkdir(parents=True, exist_ok=True)
        trainable_weights: dict[str, mx.array] = dict(
            mx_utils.tree_flatten(self._model.trainable_parameters())
        )
        mx.save_safetensors(
            str(out_path / self._ADAPTER_FILENAME),
            trainable_weights,
        )
        print("Training successfully completed. Adapters saved.")

    def _log_batch_progress(
            self,
            epoch: int,
            bucket_size: int,
            seen: int,
            total_batches: int,
            loss_val: float,
            elapsed: float,
    ) -> None:
        peak_gb: float = self._safe_get_peak_memory_gb()
        print(
            f"Epoch {epoch + 1}/{constants.LORA_ITERS} | "
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
        try:
            mx.clear_cache()
        except Exception:
            pass

    @staticmethod
    def _safe_reset_peak_memory() -> None:
        try:
            mx.reset_peak_memory()
        except Exception:
            pass

    @staticmethod
    def _safe_get_peak_memory_gb() -> float:
        try:
            return mx.get_peak_memory() / (1024 ** 3)
        except Exception:
            return 0.0

    def _prepare_dataset_buckets(
            self,
            data_dir: Path,
    ) -> BucketPlan:
        all_examples: list[_TrainExample] = self._load_train_examples(data_dir)
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
            data_dir: Path,
    ) -> list[_TrainExample]:
        train_file: Path = data_dir / self._TRAIN_FILENAME
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