"""Тесты для APIGateway."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

# Настраиваем алиас 'app' для api_agregator перед импортами
import api_agregator.app as api_app_module
sys.modules["app"] = api_app_module

from api_agregator.app.services.api_getaway import APIGateway


class TestAPIGateway:
    """Тесты для APIGateway."""

    @patch('api_agregator.app.services.api_getaway.requests')
    def test_make_request_success(self, mock_requests):
        """Тест успешного запроса."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_requests.request.return_value = mock_response
        
        gateway = APIGateway("http://test-service")
        result = gateway.make_request("GET", "/test")
        
        assert result == {"result": "success"}
        mock_requests.request.assert_called_once()

    @patch('api_agregator.app.services.api_getaway.requests')
    def test_make_request_with_json(self, mock_requests):
        """Тест запроса с JSON данными."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_requests.request.return_value = mock_response
        
        gateway = APIGateway("http://test-service")
        result = gateway.make_request("POST", "/test", json_data={"key": "value"})
        
        assert result == {"result": "success"}
        call_args = mock_requests.request.call_args
        assert call_args[1]["json"] == {"key": "value"}

    @patch('api_agregator.app.services.api_getaway.requests')
    def test_make_request_with_params(self, mock_requests):
        """Тест запроса с параметрами."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_requests.request.return_value = mock_response
        
        gateway = APIGateway("http://test-service")
        result = gateway.make_request("GET", "/test", params={"param1": "value1"})
        
        assert result == {"result": "success"}
        call_args = mock_requests.request.call_args
        assert call_args[1]["params"] == {"param1": "value1"}

    @patch('api_agregator.app.services.api_getaway.requests')
    def test_make_request_http_error(self, mock_requests):
        """Тест обработки HTTP ошибки."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Not found"}
        mock_response.text = "Not found"
        mock_requests.request.return_value = mock_response
        
        gateway = APIGateway("http://test-service")
        
        # HTTPException должен быть поднят, но он перехватывается и поднимается снова
        with pytest.raises(HTTPException) as exc_info:
            gateway.make_request("GET", "/test")
        
        assert exc_info.value.status_code == 404
        assert "Not found" in exc_info.value.detail

    @patch('api_agregator.app.services.api_getaway.requests.request')
    def test_make_request_timeout(self, mock_request):
        """Тест обработки таймаута."""
        from requests.exceptions import Timeout
        mock_request.side_effect = Timeout("Timeout")
        
        gateway = APIGateway("http://test-service")
        
        with pytest.raises(HTTPException) as exc_info:
            gateway.make_request("GET", "/test")
        
        assert exc_info.value.status_code == 504

    @patch('api_agregator.app.services.api_getaway.requests.request')
    def test_make_request_connection_error(self, mock_request):
        """Тест обработки ошибки подключения."""
        from requests.exceptions import ConnectionError
        mock_request.side_effect = ConnectionError("Connection error")
        
        gateway = APIGateway("http://test-service")
        
        with pytest.raises(HTTPException) as exc_info:
            gateway.make_request("GET", "/test")
        
        assert exc_info.value.status_code == 503

    @patch('api_agregator.app.services.api_getaway.requests.request')
    def test_make_request_generic_error(self, mock_request):
        """Тест обработки общей ошибки."""
        mock_request.side_effect = Exception("Generic error")
        
        gateway = APIGateway("http://test-service")
        
        with pytest.raises(HTTPException) as exc_info:
            gateway.make_request("GET", "/test")
        
        assert exc_info.value.status_code == 500

    @patch('api_agregator.app.services.api_getaway.requests')
    def test_make_request_http_error_no_json(self, mock_requests):
        """Тест обработки HTTP ошибки без JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = Exception("Not JSON")
        mock_response.text = "Internal Server Error"
        mock_requests.request.return_value = mock_response
        
        gateway = APIGateway("http://test-service")
        
        with pytest.raises(HTTPException) as exc_info:
            gateway.make_request("GET", "/test")
        
        assert exc_info.value.status_code == 500
        assert "Internal Server Error" in exc_info.value.detail

    @patch('api_agregator.app.services.api_getaway.requests')
    def test_make_request_http_error_empty_text(self, mock_requests):
        """Тест обработки HTTP ошибки с пустым текстом."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.side_effect = Exception("Not JSON")
        mock_response.text = ""
        mock_requests.request.return_value = mock_response
        
        gateway = APIGateway("http://test-service")
        
        with pytest.raises(HTTPException) as exc_info:
            gateway.make_request("GET", "/test")
        
        assert exc_info.value.status_code == 400
        assert "Unknown error" in exc_info.value.detail

