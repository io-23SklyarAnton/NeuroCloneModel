__all__ = [
    "Command",
    "CommandHandler",
]

from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.domain.entities import Bot
from common.application.base import ICommand, Response
from common.domain.value_objects import ID


class Command(ICommand):
    bot_id: ID
    lora_path: Bot.LoraPath
    reply_period: Bot.ReplyPeriod


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
        bot: Bot = await self._uow.bot.get_by_id_or_raise(command.bot_id)
        bot.attach_lora(command.lora_path)
        bot.set_reply_period(command.reply_period)

        self._uow.bot.update(bot)
        await self._uow.commit()

        return Response(
            message=f"Bot «{bot.name.value}» now uses adapter at {command.lora_path.value}. "
                    f"Reply period is set to {command.reply_period.value} seconds.",
        )
