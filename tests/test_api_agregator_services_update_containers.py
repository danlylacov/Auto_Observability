"""Тесты для UpdateContainers service."""

import sys
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

# Настраиваем алиас 'app' для api_agregator перед импортами
import api_agregator.app as api_app_module
sys.modules["app"] = api_app_module

from api_agregator.app.services.update_containers import UpdateContainers


class TestUpdateContainersExtended:
    """Расширенные тесты для UpdateContainers."""

    @patch('api_agregator.app.services.update_containers.os.getenv')
    def test_init_with_classification_url(self, mock_getenv):
        """Тест инициализации с URL классификации."""
        mock_getenv.return_value = "http://classification:8000"
        
        updater = UpdateContainers(db=None)
        
        assert updater._external_db is None
        assert updater._classification_gateway is not None

    @patch('api_agregator.app.services.update_containers.os.getenv')
    def test_init_without_classification_url(self, mock_getenv):
        """Тест инициализации без URL классификации."""
        mock_getenv.return_value = None
        
        updater = UpdateContainers(db=None)
        
        assert updater._external_db is None
        assert updater._classification_gateway is None

    @patch('api_agregator.app.services.update_containers.get_db')
    def test_get_db_external(self, mock_get_db):
        """Тест получения БД когда передана внешняя."""
        mock_db = MagicMock()
        updater = UpdateContainers(db=mock_db)
        
        result = updater._get_db()
        
        assert result == mock_db
        mock_get_db.assert_not_called()

    @patch('api_agregator.app.services.update_containers.get_db')
    def test_get_db_lazy(self, mock_get_db):
        """Тест ленивого получения БД."""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        updater = UpdateContainers(db=None)
        result = updater._get_db()
        
        assert result == mock_db
        mock_get_db.assert_called_once()

    @patch('api_agregator.app.services.update_containers.APIGateway')
    def test_classificate_container_success(self, mock_api_gateway_class):
        """Тест успешной классификации контейнера."""
        mock_gateway = MagicMock()
        mock_gateway.make_request.return_value = {"result": [["nginx", 0.9]]}
        mock_api_gateway_class.return_value = mock_gateway
        
        updater = UpdateContainers(db=None)
        container_data = {
            "Config": {
                "Labels": {"label1": "value1"},
                "Env": ["ENV=prod"],
                "Image": "nginx:latest",
                "ExposedPorts": {"80/tcp": {}}
            }
        }
        
        result = updater._classificate_container(container_data, mock_gateway)
        
        assert result == {"result": [["nginx", 0.9]]}
        mock_gateway.make_request.assert_called_once()

    @patch('api_agregator.app.services.update_containers.HostsService')
    @patch('api_agregator.app.services.update_containers.APIGateway')
    @patch('api_agregator.app.services.update_containers.DockerContainers')
    @patch('api_agregator.app.services.update_containers.os.getenv')
    def test_get_all_hosts_containers_success(self, mock_getenv, mock_docker_containers_class, 
                                             mock_api_gateway_class, mock_hosts_service_class):
        """Тест получения контейнеров со всех хостов."""
        mock_getenv.return_value = "http://classification:8000"
        
        mock_hosts_service = MagicMock()
        mock_hosts_service.get_all_hosts.return_value = {
            "host1": {"host": "localhost", "port": 8000, "name": "Host1"}
        }
        mock_hosts_service_class.return_value = mock_hosts_service
        
        mock_docker_gateway = MagicMock()
        mock_docker_gateway.make_request.return_value = {
            "containers": [{"Id": "c1", "Config": {"Image": "nginx"}}]
        }
        
        mock_classification_gateway = MagicMock()
        mock_classification_gateway.make_request.return_value = {"result": [["nginx", 0.9]]}
        
        mock_api_gateway_class.side_effect = [mock_docker_gateway, mock_classification_gateway]
        
        mock_docker_containers = MagicMock()
        mock_docker_containers_class.return_value = mock_docker_containers
        
        updater = UpdateContainers(db=None)
        updater._classification_gateway = mock_classification_gateway
        
        with patch.object(updater, '_classificate_container', return_value={"result": [["nginx", 0.9]]}):
            result = updater._get_all_hosts_containers()
            
            assert "host1" in result
            assert "c1" in result["host1"]

    @patch('api_agregator.app.services.update_containers.HostsService')
    @patch('api_agregator.app.services.update_containers.DockerContainers')
    @patch('api_agregator.app.services.update_containers.os.getenv')
    def test_upload_containers_no_hosts(self, mock_getenv, mock_docker_containers_class, mock_hosts_service_class):
        """Тест загрузки контейнеров при отсутствии хостов."""
        mock_getenv.return_value = "http://classification:8000"
        
        mock_hosts_service = MagicMock()
        mock_hosts_service.get_all_hosts.return_value = {}
        mock_hosts_service_class.return_value = mock_hosts_service
        
        mock_docker_containers = MagicMock()
        mock_client = MagicMock()
        mock_client.pipeline.return_value = MagicMock()
        mock_client.keys.return_value = []
        mock_docker_containers.client = mock_client
        mock_docker_containers_class.return_value = mock_docker_containers
        
        updater = UpdateContainers(db=None)
        updater.upload_containers()
        
        # Не должно быть ошибок при отсутствии хостов

    @patch('api_agregator.app.services.update_containers.HostsService')
    @patch('api_agregator.app.services.update_containers.APIGateway')
    @patch('api_agregator.app.services.update_containers.DockerContainers')
    @patch('api_agregator.app.services.update_containers.os.getenv')
    def test_upload_containers_success(self, mock_getenv, mock_docker_containers_class, 
                                      mock_api_gateway_class, mock_hosts_service_class):
        """Тест успешной загрузки контейнеров."""
        mock_getenv.return_value = "http://classification:8000"
        
        mock_hosts_service = MagicMock()
        mock_hosts_service.get_all_hosts.return_value = {
            "host1": {"host": "localhost", "port": 8000, "name": "Host1"}
        }
        mock_hosts_service_class.return_value = mock_hosts_service
        
        mock_docker_gateway = MagicMock()
        mock_docker_gateway.make_request.return_value = {
            "containers": [{"Id": "c1", "Config": {"Image": "nginx"}}]
        }
        mock_api_gateway_class.return_value = mock_docker_gateway
        
        mock_docker_containers = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = None
        mock_client = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline
        mock_client.keys.return_value = []
        mock_docker_containers.client = mock_client
        mock_docker_containers_class.return_value = mock_docker_containers
        
        updater = UpdateContainers(db=None)
        updater._classification_gateway = None
        
        with patch.object(updater, '_get_all_hosts_containers', return_value={
            "host1": {
                "c1": {
                    "info": {"Id": "c1"},
                    "classification": {"result": [["nginx", 0.9]]}
                }
            }
        }):
            updater.upload_containers()
            
            mock_pipeline.set.assert_called()
            mock_pipeline.execute.assert_called_once()

