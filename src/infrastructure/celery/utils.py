__all__ = [
    "task_with_custom_async",
    "validate_payload",
    "catch_exceptions",
    "set_request_id_from_task",
    "request_id_var",
    "run_async",
]

import asyncio
import contextvars
from functools import wraps
from typing import Any, Callable, Coroutine, Optional, TypeVar

from celery import Task
from celery.local import PromiseProxy
from pydantic import BaseModel

from infrastructure.celery.celery_app import celery_app

request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None,
)

T = TypeVar("T")


def task_with_custom_async(*task_args, **task_kwargs) -> Callable:
    def decorator(task_func: Callable) -> PromiseProxy:
        task = celery_app.task(name=f"{task_func.__name__}", *task_args, **task_kwargs)(task_func)

        original_apply_async = task.apply_async

        @wraps(original_apply_async)
        def custom_apply_async(
                args: tuple = (),
                kwargs: Optional[dict] = None,
                **options: dict,
        ):
            print(
                f"Publishing task {task.name} with args={args}, kwargs={kwargs}, options={options}",
            )

            if not isinstance(args, (tuple, list)):
                args = (args,)

            result = original_apply_async(args, kwargs, **options)

            if not result or not result.id:
                raise RuntimeError(f"Failed to publish task payload {result}")

            return result.id

        task.apply_async = custom_apply_async
        return task

    return decorator


def validate_payload(schema: type[BaseModel]) -> Callable:
    def decorator(task_func: Callable) -> Callable:
        @wraps(task_func)
        def wrapper(*args, **kwargs):
            payload: Optional[dict] = kwargs.pop("payload", None)
            if payload is None:
                raise RuntimeError("No payload found for validation.")

            try:
                parsed_payload: BaseModel = schema.model_validate(payload)
            except Exception as exc:
                print(
                    f"Failed to validate payload for task {task_func.__name__}: {exc}",
                )
                raise RuntimeError(f"Failed to validate payload: {exc}") from exc

            if args and isinstance(args[0], Task):
                return task_func(*args[1:], payload=parsed_payload, **kwargs)

            return task_func(*args, payload=parsed_payload, **kwargs)

        return wrapper

    return decorator


def set_request_id_from_task(task_func: Callable) -> Callable:
    @wraps(task_func)
    def wrapper(*args, **kwargs):
        if args and isinstance(args[0], Task):
            self_obj: Task = args[0]
            request_id_var.set(self_obj.request.id)
            return task_func(*args[1:], **kwargs)

        return task_func(*args, **kwargs)

    return wrapper


def catch_exceptions(is_critical: bool = False) -> Callable:
    def decorator(task_func: Callable) -> Callable:
        @wraps(task_func)
        def wrapper(*args, **kwargs):
            try:
                return task_func(*args, **kwargs)
            except Exception as exc:
                print(
                    f"Exception occurred in task {task_func.__name__}: {exc}",
                )
                raise

        return wrapper

    return decorator


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError("run_async called inside a running event loop")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)
