"""Расширенные тесты для HostsService."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# Настраиваем алиас 'app' для api_agregator перед импортами
import api_agregator.app as api_app_module
sys.modules["app"] = api_app_module

from api_agregator.app.services.hosts_service import HostsService, HostDTO


class TestHostsServiceExtended:
    """Расширенные тесты для HostsService."""

    def test_get_all_hosts_from_db(self, mock_db_session):
        """Тест получения всех хостов из БД."""
        mock_host1 = SimpleNamespace(id="h1", name="host1", host="localhost", port=8000)
        mock_host2 = SimpleNamespace(id="h2", name="host2", host="192.168.1.1", port=8000)
        
        mock_query = MagicMock()
        mock_query.all.return_value = [mock_host1, mock_host2]
        mock_db_session.query.return_value = mock_query
        
        service = HostsService(db=mock_db_session)
        result = service.get_all_hosts_from_db()
        
        assert len(result) == 2
        assert result[0].id == "h1"
        assert result[1].id == "h2"

    def test_get_host_by_id_found(self, mock_db_session):
        """Тест получения хоста по ID (найден)."""
        mock_host = SimpleNamespace(id="h1", name="host1", host="localhost", port=8000)
        
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_host
        mock_db_session.query.return_value = mock_query
        
        service = HostsService(db=mock_db_session)
        result = service.get_host_by_id("h1")
        
        assert result is not None
        assert result.id == "h1"
        assert result.name == "host1"

    def test_get_host_by_id_not_found(self, mock_db_session):
        """Тест получения хоста по ID (не найден)."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query
        
        service = HostsService(db=mock_db_session)
        result = service.get_host_by_id("nonexistent")
        
        assert result is None

    @patch('api_agregator.app.services.hosts_service.requests')
    def test_check_host_status_online(self, mock_requests, mock_db_session):
        """Тест проверки статуса хоста (онлайн)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response
        
        service = HostsService(db=mock_db_session)
        status = service.check_host_status("h1", "localhost", 8000)
        
        assert status == "online"

    @patch('api_agregator.app.services.hosts_service.requests')
    def test_check_host_status_offline(self, mock_requests, mock_db_session):
        """Тест проверки статуса хоста (офлайн)."""
        mock_requests.get.side_effect = Exception("Connection error")
        
        service = HostsService(db=mock_db_session)
        status = service.check_host_status("h1", "localhost", 8000)
        
        assert status == "offline"

    @patch('api_agregator.app.services.hosts_service.os.path.exists')
    def test_resolve_host_for_docker_not_docker(self, mock_exists, mock_db_session):
        """Тест разрешения хоста для Docker (не в Docker)."""
        mock_exists.return_value = False
        
        service = HostsService(db=mock_db_session)
        result = service._resolve_host_for_docker("localhost")
        
        assert result == "localhost"

    @patch('api_agregator.app.services.hosts_service.os.path.exists')
    def test_resolve_host_for_docker_in_docker(self, mock_exists, mock_db_session):
        """Тест разрешения хоста для Docker (в Docker)."""
        mock_exists.return_value = True
        
        service = HostsService(db=mock_db_session)
        result = service._resolve_host_for_docker("localhost")
        
        assert result == "host.docker.internal"

    def test_upload_hosts(self, mock_db_session):
        """Тест загрузки хостов в Redis."""
        mock_host1 = SimpleNamespace(id="h1", name="host1", host="localhost", port=8000)
        
        mock_query = MagicMock()
        mock_query.all.return_value = [mock_host1]
        mock_db_session.query.return_value = mock_query
        
        service = HostsService(db=mock_db_session)
        service.redis_hosts = MagicMock()
        
        with patch.object(service, 'check_host_status', return_value="online"):
            result = service.upload_hosts()
            
            assert "h1" in result
            assert result["h1"]["name"] == "host1"

    def test_add_host_to_redis(self, mock_db_session):
        """Тест добавления хоста в Redis."""
        service = HostsService(db=mock_db_session)
        service.redis_hosts = MagicMock()
        
        service.add_host_to_redis("h1", "host1", "localhost", 8000)
        
        service.redis_hosts.upload_hosts.assert_called_once()

    def test_get_all_hosts(self, mock_db_session):
        """Тест получения всех хостов из Redis."""
        service = HostsService(db=mock_db_session)
        service.redis_hosts = MagicMock()
        service.redis_hosts.get_hosts.return_value = {"h1": {"name": "host1"}}
        
        result = service.get_all_hosts()
        
        assert "h1" in result
        assert result["h1"]["name"] == "host1"

    @patch('api_agregator.app.services.hosts_service.requests.get')
    def test_check_host_status_timeout_localhost(self, mock_get):
        """Тест проверки статуса хоста с таймаутом для localhost."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")
        
        service = HostsService(db=MagicMock())
        result = service.check_host_status("h1", "localhost", 8000)
        
        assert result == "local_only"

    @patch('api_agregator.app.services.hosts_service.requests.get')
    def test_check_host_status_connection_error_localhost(self, mock_get):
        """Тест проверки статуса хоста с ошибкой подключения для localhost."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection error")
        
        service = HostsService(db=MagicMock())
        result = service.check_host_status("h1", "localhost", 8000)
        
        assert result == "local_only"

    @patch('api_agregator.app.services.hosts_service.requests.get')
    def test_check_host_status_exception_localhost(self, mock_get):
        """Тест проверки статуса хоста с исключением для localhost."""
        mock_get.side_effect = Exception("Generic error")
        
        service = HostsService(db=MagicMock())
        result = service.check_host_status("h1", "localhost", 8000)
        
        assert result == "local_only"

    @patch('api_agregator.app.services.hosts_service.requests.get')
    def test_check_host_status_127_0_0_1(self, mock_get):
        """Тест проверки статуса хоста для 127.0.0.1."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection error")
        
        service = HostsService(db=MagicMock())
        result = service.check_host_status("h1", "127.0.0.1", 8000)
        
        assert result == "local_only"

    @patch('api_agregator.app.services.hosts_service.requests.get')
    def test_upload_hosts_timeout(self, mock_get):
        """Тест загрузки хостов с таймаутом."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")
        
        mock_db_session = MagicMock()
        mock_host = MagicMock()
        mock_host.id = "h1"
        mock_host.name = "Host1"
        mock_host.host = "localhost"
        mock_host.port = 8000
        mock_db_session.query.return_value.all.return_value = [mock_host]
        
        service = HostsService(db=mock_db_session)
        service.redis_hosts = MagicMock()
        result = service.upload_hosts()
        
        assert "h1" in result
        assert result["h1"]["status"] == "timeout"

    @patch('api_agregator.app.services.hosts_service.requests.get')
    def test_upload_hosts_connection_error(self, mock_get):
        """Тест загрузки хостов с ошибкой подключения."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection error")
        
        mock_db_session = MagicMock()
        mock_host = MagicMock()
        mock_host.id = "h1"
        mock_host.name = "Host1"
        mock_host.host = "localhost"
        mock_host.port = 8000
        mock_db_session.query.return_value.all.return_value = [mock_host]
        
        service = HostsService(db=mock_db_session)
        service.redis_hosts = MagicMock()
        result = service.upload_hosts()
        
        assert "h1" in result
        assert result["h1"]["status"] == "down"

    @patch('api_agregator.app.services.hosts_service.requests.get')
    def test_upload_hosts_generic_exception(self, mock_get):
        """Тест загрузки хостов с общим исключением."""
        mock_get.side_effect = Exception("Generic error")
        
        mock_db_session = MagicMock()
        mock_host = MagicMock()
        mock_host.id = "h1"
        mock_host.name = "Host1"
        mock_host.host = "localhost"
        mock_host.port = 8000
        mock_db_session.query.return_value.all.return_value = [mock_host]
        
        service = HostsService(db=mock_db_session)
        service.redis_hosts = MagicMock()
        result = service.upload_hosts()
        
        assert "h1" in result
        assert result["h1"]["status"] == "down"

