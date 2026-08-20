from pydantic import BaseModel


class RenameExampleResourcePayload(BaseModel):
    title: str = ""
