import abc

from domain.value_objects import ID
from features.interfaces.repositories import IBaseRepository


class IThreadRepository(IBaseRepository):
    @abc.abstractmethod
    def get_thread_by_id(self, thread_id: ID):
        pass
