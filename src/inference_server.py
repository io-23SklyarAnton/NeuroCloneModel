import asyncio
import logging
from typing import Any

from aiohttp import web

import config
import constants
from infrastructure.llm.cuda_engine import CUDAInferenceEngine


_logger = logging.getLogger("inference_server")

_ENGINE_KEY: web.AppKey[CUDAInferenceEngine] = web.AppKey("engine", CUDAInferenceEngine)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _resolve_base_model() -> constants.AvailableModel:
    raw: str = config.INFERENCE_BASE_MODEL
    try:
        return constants.AvailableModel(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Unsupported INFERENCE_BASE_MODEL='{raw}'. "
            f"Allowed: {[m.value for m in constants.AvailableModel]}"
        ) from exc


async def _generate_handler(request: web.Request) -> web.Response:
    engine: CUDAInferenceEngine = request.app[_ENGINE_KEY]
    payload: dict[str, Any] = await request.json()

    text: str = await engine.generate_async(
        system_prompt=payload["system_prompt"],
        user_prompt=payload["user_prompt"],
        lora_path=payload.get("lora_path"),
        max_tokens=int(payload["max_tokens"]),
        temp=float(payload["temp"]),
        priority=int(payload["priority"]),
        assistant_prefill=payload.get("assistant_prefill", ""),
    )
    return web.json_response({"text": text})


async def _train_lora_handler(request: web.Request) -> web.Response:
    engine: CUDAInferenceEngine = request.app[_ENGINE_KEY]
    payload: dict[str, Any] = await request.json()

    await engine.train_lora(
        train_data_path=payload["train_data_path"],
        adapter_path=payload["adapter_path"],
    )
    return web.json_response({"status": "completed"})


async def _health_handler(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def _build_app(base_model: constants.AvailableModel) -> web.Application:
    app: web.Application = web.Application(
        client_max_size=10 * 1024 * 1024,
    )
    engine: CUDAInferenceEngine = CUDAInferenceEngine(base_model=base_model)
    app[_ENGINE_KEY] = engine

    app.router.add_post("/generate", _generate_handler)
    app.router.add_post("/train_lora", _train_lora_handler)
    app.router.add_get("/health", _health_handler)

    return app


def main() -> None:
    _setup_logging()
    base_model: constants.AvailableModel = _resolve_base_model()
    _logger.info("Starting inference server with base model: %s", base_model.value)

    app: web.Application = _build_app(base_model)

    web.run_app(
        app,
        host=config.INFERENCE_SERVER_HOST,
        port=config.INFERENCE_SERVER_PORT,
        access_log=_logger,
        handle_signals=True,
        shutdown_timeout=5.0,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except asyncio.CancelledError:
        pass
