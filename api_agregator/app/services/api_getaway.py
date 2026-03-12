import logging
from typing import Optional, Dict, Any

import requests
from fastapi import HTTPException
from starlette import status

logger = logging.getLogger(__name__)


class APIGateway:
    """
    Класс для выполнения HTTP запросов к внешним сервисам.

    Предоставляет единый интерфейс для взаимодействия с микросервисами.
    """

    def __init__(self, service_url: str):
        """
        Инициализация API Gateway.

        Args:
            service_url: Базовый URL сервиса
        """
        self.base_url = service_url
        self.timeout = 5

    def make_request(
            self,
            method: str,
            endpoint: str,
            data: Optional[Dict] = None,
            params: Optional[Dict] = None,
            json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Базовый метод для выполнения HTTP запросов к сервису.

        Args:
            method: HTTP метод (GET, POST, PUT, DELETE и т.д.)
            endpoint: Путь к эндпоинту
            data: Данные для отправки в теле запроса (form-data)
            params: Параметры запроса (query string)
            json_data: JSON данные для отправки в теле запроса

        Returns:
            Dict[str, Any]: Ответ от сервиса в виде словаря

        Raises:
            HTTPException: При ошибках запроса или ответа от сервиса
        """
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Making {method} request to {url}")
        if json_data:
            logger.debug(f"Request JSON data: {json_data}")

        try:
            response = requests.request(
                method=method,
                url=url,
                data=data,
                params=params,
                json=json_data,
                timeout=self.timeout
            )

            logger.info(f"Response status: {response.status_code}")

            if response.status_code >= 400:
                try:
                    # Пытаемся извлечь детальное сообщение об ошибке из JSON
                    error_json = response.json()
                    error_detail = error_json.get('detail', response.text)
                    logger.error(f"Service returned error: {error_detail}")
                except Exception:
                    error_detail = response.text or "Unknown error"

                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )

            return response.json()

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout to {url}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Request to service timed out: {url}"
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to {url}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot connect to service at {url}. Please check if the service is running."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error to {url}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Request error: {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in API Gateway: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal gateway error: {str(e)}"
            )
