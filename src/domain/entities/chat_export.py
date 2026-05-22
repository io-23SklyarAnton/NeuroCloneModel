__all__ = ["ChatExport"]

from typing import TYPE_CHECKING

from domain.entities.base import Aggregate
from domain.value_objects import ExportFileKey

if TYPE_CHECKING:
    from domain.entities import User, Chat


class ChatExport(Aggregate):
    def __init__(
            self,
            chat_id: "Chat.ExternalID",
            owner_id: "User.TelegramID",
            export_file_key: ExportFileKey,
            is_disentangled: bool,
    ):
        super().__init__()
        self._chat_id = chat_id
        self._owner_id = owner_id
        self._export_file_key = export_file_key
        self._is_disentangled = is_disentangled

    @property
    def id(self) -> "Chat.ExternalID":
        return self._chat_id

    @property
    def chat_id(self) -> "Chat.ExternalID":
        return self._chat_id

    @property
    def owner_id(self) -> "User.TelegramID":
        return self._owner_id

    @property
    def export_file_key(self) -> ExportFileKey:
        return self._export_file_key

    @property
    def is_disentangled(self) -> bool:
        return self._is_disentangled

    @classmethod
    def create(
            cls,
            chat_id: "Chat.ExternalID",
            owner_id: "User.TelegramID",
            export_file_key: ExportFileKey,
    ) -> "ChatExport":
        return cls(
            chat_id=chat_id,
            owner_id=owner_id,
            export_file_key=export_file_key,
            is_disentangled=False,
        )
