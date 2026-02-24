from pydantic import BaseModel, Field
from typing import Optional, Dict


class Container(BaseModel):
    id: str = Field(None, max_length=500)


class Volume(BaseModel):
    name: str = Field(None, max_length=500)


class FullContainer(BaseModel):
    image_name: str = Field(None, max_length=500)
    command: Optional[str] = Field(None, max_length=500)
    name: Optional[str] = Field(None, max_length=500)
    detach: bool = Field(True)
    ports: Optional[Dict[str, int]] = Field(None)
    volumes: Optional[Dict[str, Dict[str, str]]] = Field(None)
    environment: Optional[Dict[str, str]] = Field(None)
