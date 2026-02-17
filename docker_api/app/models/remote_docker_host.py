from pydantic import BaseModel, Field
from typing import Optional


class RemoteHost(BaseModel):
    address: Optional[str] = Field(None, max_length=40)
    username: Optional[str] = Field(None, max_length=40)
