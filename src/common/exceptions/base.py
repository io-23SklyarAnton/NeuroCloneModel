__all__ = [
    "BaseAppException",
    "UnexpectedError",
]


class BaseAppException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return self.message


class UnexpectedError(BaseAppException):
    def __init__(self, message: str = "An unexpected error occurred"):
        super().__init__(message)
