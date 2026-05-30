__all__ = [
    "Command",
    "CommandHandler",
]

from pathlib import Path

from common.application.base import ICommand, Response
from common.application.interfaces import IStorage
from common.domain.value_objects import FileReference, ID
from infrastructure.llm import IInferenceEngine
from model_engine.application.interfaces import IUnitOfWork
from model_engine.domain.entities import NeuroClone

_ADAPTERS_BUCKET = "adapters"


class Command(ICommand):
    neuroclone_id: ID


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
            inference_engine: IInferenceEngine,
            storage: IStorage,
    ) -> None:
        self._uow = uow
        self._inference_engine = inference_engine
        self._storage = storage

    async def handle(
            self,
            command: Command,
    ) -> Response:
        neuroclone: NeuroClone = await self._uow.neuroclone.get_by_id_or_raise(command.neuroclone_id)
        neuroclone.start_training()
        self._uow.neuroclone.update(neuroclone)
        await self._uow.commit()

        adapter_file_reference: FileReference = self._build_adapter_file_reference(neuroclone_id=neuroclone.id)
        train_data_path: Path = self._storage.resolve_local_path(neuroclone.dataset_file_reference)
        adapter_path: Path = self._storage.resolve_local_path(adapter_file_reference)

        try:
            await self._inference_engine.train_lora(
                train_data_path=str(train_data_path),
                adapter_path=str(adapter_path),
            )
        except Exception as exc:
            neuroclone.mark_failed()
            self._uow.neuroclone.update(neuroclone)
            await self._uow.commit()
            print(f"Error during training NeuroClone {neuroclone.id.value}: {exc}")
            return Response(
                message=f"NeuroClone {neuroclone.id.value} training failed: {exc}",
            )

        neuroclone.set_adapter_file_reference(adapter_file_reference)
        neuroclone.mark_ready()
        self._uow.neuroclone.update(neuroclone)
        await self._uow.commit()

        return Response(
            message=f"NeuroClone {neuroclone.id.value} is now {neuroclone.status.value}.",
        )

    @staticmethod
    def _build_adapter_file_reference(neuroclone_id: ID) -> FileReference:
        return FileReference(
            bucket=_ADAPTERS_BUCKET,
            key=f"{neuroclone_id.value}.safetensors",
        )
