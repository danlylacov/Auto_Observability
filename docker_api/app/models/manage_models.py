from pydantic import BaseModel, Field


class Container(BaseModel):
    id: str = Field(None, max_length=500)


class Volume(BaseModel):
    name: str = Field(None, max_length=500)
