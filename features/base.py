__all__ = ["ICommand"]

import pydantic


class ICommand(pydantic.BaseModel):
    ...
