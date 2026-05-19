from pathlib import Path

from features.base import ICommand
from llm import IInferenceEngine


class Command(ICommand):
    train_data_path: Path
    adapter_path: Path


class CommandHandler:
    def __init__(self, inference_engine: IInferenceEngine) -> None:
        self._inference_engine = inference_engine

    async def handle(self, command: Command) -> None:
        await self._inference_engine.train_lora(
            train_data_path=str(command.train_data_path),
            adapter_path=str(command.adapter_path),
        )
