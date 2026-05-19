__all__ = ["ICommand", "Response"]

import pydantic


class ICommand(pydantic.BaseModel):
    ...


class Response(pydantic.BaseModel):
    message: str
