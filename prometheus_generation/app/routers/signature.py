import os
import logging
from typing import Dict

import yaml
from fastapi import APIRouter, status
from app.services.signature import Signature


router = APIRouter()
logger = logging.getLogger(__name__)


@router.patch("/update", status_code=status.HTTP_200_OK)
async def generate(new_signature: str) -> Dict[str, str]:
    signature = Signature()
    try:
        signature.update(new_signature)
        return {"result": "success"}
    except Exception as e:
        return {"result": str(e)}


@router.get("/get", status_code=status.HTTP_200_OK)
async def get() -> Dict[str, str]:
    signature = Signature()
    try:
        return {"signature.yml": signature.get()}
    except Exception as e:
        return {"signature.yml": str(e)}



