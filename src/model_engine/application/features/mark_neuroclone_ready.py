__all__ = [
    "Command",
    "CommandHandler",
]

from common.application.base import ICommand, Response
from common.domain.value_objects import ID
from model_engine.application.interfaces import IUnitOfWork
from model_engine.domain.entities import NeuroClone


class Command(ICommand):
    neuroclone_id: ID
    adapter_path: NeuroClone.AdapterPath


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
    ) -> None:
        self._uow = uow

    async def handle(
            self,
            command: Command,
    ) -> Response:
        neuroclone: NeuroClone = await self._uow.neuroclone.get_by_id_or_raise(command.neuroclone_id)
        neuroclone.mark_ready(command.adapter_path)

        self._uow.neuroclone.update(neuroclone)
        await self._uow.commit()

        return Response(
            message=f"NeuroClone {neuroclone.id.value} is now {neuroclone.status.value}.",
        )
