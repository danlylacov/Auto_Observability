import asyncio
from typing import Optional, Dict, Any

import aiohttp
from fastapi import HTTPException
from starlette import status
from watchfiles import awatch


class APIGateway:
    def __init__(self, service_url: str):
        self.base_url = service_url
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def make_request(
            self,
            method: str,
            endpoint: str,
            data: Optional[Dict] = None,
            params: Optional[Dict] = None,
            json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Базовый метод для выполнения HTTP запросов к Docker сервису
        """
        url = f"{self.base_url}{endpoint}"

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.request(
                        method=method,
                        url=url,
                        data=data,
                        params=params,
                        json=json_data
                ) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Docker service error: {error_text}"
                        )

                    return await response.json()

        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Docker service timeout"
            )
        except aiohttp.ClientConnectorError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Docker service unavailable: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal gateway error: {str(e)}"
            )

DOCKER_SERVICE_URL = "http://localhost:8000"
docker_gateway = APIGateway(DOCKER_SERVICE_URL)
async def main():
    result = await docker_gateway.make_request(
        method="POST",
        endpoint="/api/v1/manage/container/start",
        json_data={  # Используйте json_data вместо data для отправки JSON
            "container": {
                "id": "6ba835ea0ff327b7effc79d54252a7c7bfaf99d71456bcfe697d09622532fe6f"
            }
        }
    )
    print(result)

# Вариант 2: Если вам нужно вызвать из синхронного кода
if __name__ == "__main__":
    asyncio.run(main())