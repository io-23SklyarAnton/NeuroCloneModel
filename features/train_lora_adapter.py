from pathlib import Path

from features.base import ICommand
from llm import IInferenceEngine


class Command(ICommand):
    data_dir: Path
    adapter_path: Path


class CommandHandler:
    def __init__(self, inference_engine: IInferenceEngine) -> None:
        self._inference_engine = inference_engine

    async def handle(self, command: Command) -> None:
        command.adapter_path.mkdir(parents=True, exist_ok=True)
        await self._inference_engine.train_lora(
            data_dir=str(command.data_dir),
            adapter_path=str(command.adapter_path),
        )
