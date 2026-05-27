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

        adapter_path: str = self._build_adapter_path(neuroclone_id=neuroclone.id)

        try:
            await self._inference_engine.train_lora(
                train_data_path=str(neuroclone.dataset_file_key),
                adapter_path=adapter_path,
            )
        except Exception as exc:
            neuroclone.mark_failed()
            self._uow.neuroclone.update(neuroclone)
            await self._uow.commit()
            return Response(
                message=f"NeuroClone {neuroclone.id.value} training failed: {exc}",
            )

        neuroclone.set_adapter_path(NeuroClone.AdapterPath(value=str(adapter_path)))
        neuroclone.mark_ready()
        self._uow.neuroclone.update(neuroclone)
        await self._uow.commit()

        return Response(
            message=f"NeuroClone {neuroclone.id.value} is now {neuroclone.status.value}.",
        )

    def _build_adapter_path(self, neuroclone_id: ID) -> str:
        base_path = Path("/adapters")
        adapter_file_name = f"{neuroclone_id.value}.safetensors"
        return str(base_path / adapter_file_name)
