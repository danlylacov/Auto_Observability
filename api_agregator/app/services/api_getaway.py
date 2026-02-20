from typing import Optional, Dict, Any
import requests
from fastapi import HTTPException
from starlette import status


class APIGateway:
    def __init__(self, service_url: str):
        self.base_url = service_url
        self.timeout = 30

    def make_request(
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
            # Выполняем синхронный запрос
            response = requests.request(
                method=method,
                url=url,
                data=data,
                params=params,
                json=json_data,
                timeout=self.timeout
            )

            # Проверяем статус ответа
            if response.status_code >= 400:
                try:
                    error_text = response.text
                except:
                    error_text = "Unknown error"

                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Docker service error: {error_text}"
                )

            # Возвращаем JSON ответ
            return response.json()

        except requests.exceptions.Timeout:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request to Docker service timed out"
            )
        except requests.exceptions.ConnectionError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cannot connect to Docker service"
            )
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Request error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal gateway error: {str(e)}"
            )


DOCKER_SERVICE_URL = "http://localhost:8000"
docker_gateway = APIGateway(DOCKER_SERVICE_URL)


def main():
    try:
        result = docker_gateway.make_request(
            method="POST",
            endpoint="/api/v1/manage/container/start",
            json_data={
                "container": {
                    "id": "6ba835ea0ff327b7effc79d54252a7c7bfaf99d71456bcfe697d09622532fe6f"
                }
            }
        )
        print("Response:", result)
    except HTTPException as e:
        print(f"Error: {e.detail}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()