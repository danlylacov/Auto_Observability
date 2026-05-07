"""Тесты для Celery задач API Aggregator."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Настраиваем алиас 'app' для api_agregator перед импортами
import api_agregator.app as api_app_module
sys.modules["app"] = api_app_module

from api_agregator.app.tasks.update_containers import update_containers
from api_agregator.app.tasks.update_hosts import update_hosts


class TestCeleryTasks:
    """Тесты для Celery задач."""

    @patch('api_agregator.app.tasks.update_containers.UpdateContainers')
    def test_update_containers_task(self, mock_update_containers_class):
        """Тест задачи обновления контейнеров."""
        mock_service = MagicMock()
        mock_update_containers_class.return_value = mock_service
        
        update_containers()
        
        mock_update_containers_class.assert_called_once()
        mock_service.upload_containers.assert_called_once()

    @patch('api_agregator.app.tasks.update_hosts.SessionLocal')
    @patch('api_agregator.app.tasks.update_hosts.HostsService')
    def test_update_hosts_task(self, mock_hosts_service_class, mock_session_local):
        """Тест задачи обновления хостов."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_hosts_service = MagicMock()
        mock_hosts_service.upload_hosts.return_value = {}
        mock_hosts_service_class.return_value = mock_hosts_service
        
        update_hosts()
        
        mock_hosts_service_class.assert_called_once_with(mock_db)
        mock_hosts_service.upload_hosts.assert_called_once()
        mock_db.close.assert_called_once()

    @patch('api_agregator.app.tasks.update_hosts.SessionLocal')
    @patch('api_agregator.app.tasks.update_hosts.HostsService')
    def test_update_hosts_task_exception(self, mock_hosts_service_class, mock_session_local):
        """Тест задачи обновления хостов при исключении."""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        mock_hosts_service = MagicMock()
        mock_hosts_service.upload_hosts.side_effect = Exception("Test error")
        mock_hosts_service_class.return_value = mock_hosts_service
        
        with pytest.raises(Exception):
            update_hosts()
        
        mock_db.close.assert_called_once()

