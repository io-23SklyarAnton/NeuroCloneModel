from exceptions.base import BaseAppException


class BaseClientError(BaseAppException):
    def __init__(self, message: str):
        super().__init__(message)

    def __str__(self) -> str:
        return f"Client error: {self.message}"
