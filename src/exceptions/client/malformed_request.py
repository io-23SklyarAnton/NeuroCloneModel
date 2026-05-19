from exceptions.client.base import BaseClientError


class MalformedRequestException(BaseClientError):
    def __init__(self, message: str):
        super().__init__(message)

    def __str__(self) -> str:
        return f"Malformed request: {self.message}"


class MissingUserException(MalformedRequestException):
    def __init__(self):
        super().__init__("User is missing in the request")
