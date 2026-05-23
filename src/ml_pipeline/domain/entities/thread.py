__all__ = ["Thread"]

from ml_pipeline.application import constants
from common.domain.entities import Aggregate
from common.domain.value_objects import ID
from ml_pipeline.domain.entities.chat_export import ChatExport, ParsedMessage


class Thread(Aggregate):
    def __init__(
            self,
            id_: ID,
            chat_export_id: ChatExport.ChatID,
            recent_messages: list[ParsedMessage],
    ):
        super().__init__()
        self._id = id_
        self._chat_export_id = chat_export_id
        self._recent_messages = recent_messages

        self._messages_to_add: list[ParsedMessage] = []

    @property
    def id(self) -> ID:
        return self._id

    @property
    def chat_export_id(self) -> ChatExport.ChatID:
        return self._chat_export_id

    @property
    def recent_messages(self) -> list[ParsedMessage]:
        return self._recent_messages

    @property
    def uncommitted_messages(self) -> list[ParsedMessage]:
        return self._messages_to_add

    @classmethod
    def create(
            cls,
            message: ParsedMessage,
    ) -> "Thread":
        return cls(
            id_=ID.create(),
            chat_export_id=message.chat_export_id,
            recent_messages=[],
        )

    def add_message(
            self,
            message: ParsedMessage,
    ) -> None:
        self._messages_to_add.append(message)

        self._recent_messages.append(message)
        self._recent_messages = self._recent_messages[-constants.N_RECENT_MESSAGES:]
