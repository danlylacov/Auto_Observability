from typing import Dict, Any
from pydantic import BaseModel


class AddServiceRequest(BaseModel):
    scrape_config: Dict[str, Any]
    target: list | dict
    target_name: str


class RemoveServiceRequest(BaseModel):
    job_name: str
    target_name: str
