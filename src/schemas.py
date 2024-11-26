import uuid

from pydantic import BaseModel, ConfigDict


class FileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    format: str
    extension: str
    size: int
