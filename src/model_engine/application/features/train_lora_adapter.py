__all__ = [
    "Command",
    "CommandHandler",
]

from pathlib import Path

from common.application.base import ICommand, Response
from common.domain.value_objects import ID
from infrastructure.llm import IInferenceEngine
from model_engine.application.interfaces import IUnitOfWork
from model_engine.domain.entities import NeuroClone


class Command(ICommand):
    neuroclone_id: ID
    train_data_path: Path
    adapter_path: Path


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
            inference_engine: IInferenceEngine,
    ) -> None:
        self._uow = uow
        self._inference_engine = inference_engine

    async def handle(
            self,
            command: Command,
    ) -> Response:
        neuroclone: NeuroClone = await self._uow.neuroclone.get_by_id_or_raise(command.neuroclone_id)
        neuroclone.start_training()
        self._uow.neuroclone.update(neuroclone)
        await self._uow.commit()

        try:
            await self._inference_engine.train_lora(
                train_data_path=str(command.train_data_path),
                adapter_path=str(command.adapter_path),
            )
        except Exception as exc:
            neuroclone.mark_failed()
            self._uow.neuroclone.update(neuroclone)
            await self._uow.commit()
            return Response(
                message=f"NeuroClone {neuroclone.id.value} training failed: {exc}",
            )

        neuroclone.mark_ready(NeuroClone.AdapterPath(value=str(command.adapter_path)))
        self._uow.neuroclone.update(neuroclone)
        await self._uow.commit()

        return Response(
            message=f"NeuroClone {neuroclone.id.value} is now {neuroclone.status.value}.",
        )
