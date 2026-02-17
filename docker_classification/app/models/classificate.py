from typing import Dict, List

from pydantic import BaseModel, Field


class ContainerInspectData(BaseModel):
    """
    Модель для данных инспекции контейнера от Docker Compose.
    """
    labels: Dict[str, str] = Field(
        ...,
        description="Docker Compose labels",
        examples=[{
            "com.docker.compose.service": "frontend",
            "com.docker.compose.project": "k1-test"
        }]
    )

    envs: List[str] = Field(
        ...,
        description="Environment variables as KEY=value strings"
    )

    image: str = Field(
        ...,
        description="Container image name",
        min_length=1,
        examples=["k1-test-frontend", "nginx:latest"]
    )

    ports: List[str] = Field(
        ...,
        description="Container ports",
        examples=["3000", "3000/tcp", "80:8080"]
    )