"""Тесты для сервисов grafana_generation."""

import sys
from unittest.mock import MagicMock, patch, mock_open
import pytest
import json
import os

# Настраиваем алиас 'app' для grafana_generation перед импортами
import grafana_generation.app as grafana_generation_app_module
sys.modules["app"] = grafana_generation_app_module

from grafana_generation.app.services.templste_loader import GrafanaTemplateLoader


class TestGrafanaTemplateLoader:
    """Тесты для GrafanaTemplateLoader."""

    @patch('grafana_generation.app.services.templste_loader.os.makedirs')
    def test_init_default_cache_dir(self, mock_makedirs):
        """Тест инициализации с путем кэша по умолчанию."""
        loader = GrafanaTemplateLoader()
        
        assert loader.cache_dir == "./.dashboard_cache"
        mock_makedirs.assert_called_once_with("./.dashboard_cache", exist_ok=True)

    @patch('grafana_generation.app.services.templste_loader.os.makedirs')
    def test_init_custom_cache_dir(self, mock_makedirs):
        """Тест инициализации с кастомным путем кэша."""
        loader = GrafanaTemplateLoader(cache_dir="/custom/cache")
        
        assert loader.cache_dir == "/custom/cache"
        mock_makedirs.assert_called_once_with("/custom/cache", exist_ok=True)

    @patch('grafana_generation.app.services.templste_loader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"dashboard": "test"}')
    def test_fetch_dashboard_json_from_cache(self, mock_file, mock_exists):
        """Тест загрузки дашборда из кэша."""
        mock_exists.return_value = True
        
        loader = GrafanaTemplateLoader(cache_dir="/test/cache")
        result = loader.fetch_dashboard_json(9628, revision=1)
        
        assert result == {"dashboard": "test"}
        mock_file.assert_called_once_with("/test/cache/9628_r1.json", 'r', encoding='utf-8')

    @patch('grafana_generation.app.services.templste_loader.requests.get')
    @patch('grafana_generation.app.services.templste_loader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_fetch_dashboard_json_download(self, mock_file, mock_exists, mock_get):
        """Тест скачивания дашборда с grafana.com."""
        mock_exists.return_value = False
        
        # Мок для получения метаданных
        mock_meta_response = MagicMock()
        mock_meta_response.status_code = 200
        mock_meta_response.json.return_value = {"revision": 2}
        
        # Мок для скачивания дашборда
        mock_download_response = MagicMock()
        mock_download_response.status_code = 200
        mock_download_response.json.return_value = {"dashboard": "downloaded"}
        
        mock_get.side_effect = [mock_meta_response, mock_download_response]
        
        loader = GrafanaTemplateLoader(cache_dir="/test/cache")
        result = loader.fetch_dashboard_json(9628)
        
        assert result == {"dashboard": "downloaded"}
        assert mock_get.call_count == 2

    @patch('grafana_generation.app.services.templste_loader.requests.get')
    @patch('grafana_generation.app.services.templste_loader.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_fetch_dashboard_json_with_revision(self, mock_file, mock_exists, mock_get):
        """Тест скачивания дашборда с указанной ревизией."""
        mock_exists.return_value = False
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"dashboard": "revision1"}
        mock_get.return_value = mock_response
        
        loader = GrafanaTemplateLoader(cache_dir="/test/cache")
        result = loader.fetch_dashboard_json(9628, revision=1)
        
        assert result == {"dashboard": "revision1"}
        mock_get.assert_called_once()

    def test_prepare_for_import_basic(self):
        """Тест подготовки дашборда к импорту."""
        loader = GrafanaTemplateLoader()
        
        dashboard = {
            "id": 123,
            "uid": "test-uid",
            "title": "Test Dashboard",
            "version": 5,
            "panels": []
        }
        
        result = loader.prepare_for_import(
            dashboard,
            ds_uid="prometheus-uid",
            instance_suffix="host1"
        )
        
        assert "id" not in result
        assert result["version"] == 0
        assert result["uid"] == "test-uid-host1"
        assert result["title"] == "Test Dashboard [host1]"

    def test_prepare_for_import_with_title_prefix(self):
        """Тест подготовки дашборда с префиксом заголовка."""
        loader = GrafanaTemplateLoader()
        
        dashboard = {
            "uid": "test-uid",
            "title": "Test Dashboard",
            "panels": []
        }
        
        result = loader.prepare_for_import(
            dashboard,
            ds_uid="prometheus-uid",
            instance_suffix="host1",
            title_prefix="Production"
        )
        
        assert result["title"] == "Production: Test Dashboard"

    def test_prepare_for_import_replace_datasource_uid(self):
        """Тест замены UID источника данных."""
        loader = GrafanaTemplateLoader()
        
        dashboard = {
            "panels": [
                {
                    "targets": [
                        {
                            "datasource": {
                                "uid": "old-uid",
                                "type": "prometheus"
                            }
                        }
                    ]
                }
            ]
        }
        
        result = loader.prepare_for_import(
            dashboard,
            ds_uid="new-uid",
            instance_suffix="host1"
        )
        
        assert result["panels"][0]["targets"][0]["datasource"]["uid"] == "new-uid"

    def test_prepare_for_import_replace_string_datasource(self):
        """Тест замены строкового источника данных."""
        loader = GrafanaTemplateLoader()
        
        dashboard = {
            "panels": [
                {
                    "targets": [
                        {
                            "datasource": "old-uid"
                        }
                    ]
                }
            ]
        }
        
        result = loader.prepare_for_import(
            dashboard,
            ds_uid="new-uid",
            instance_suffix="host1"
        )
        
        assert result["panels"][0]["targets"][0]["datasource"]["uid"] == "new-uid"
        assert result["panels"][0]["targets"][0]["datasource"]["type"] == "prometheus"

    def test_replace_datasource_uids_nested_panels(self):
        """Тест замены UID в вложенных панелях."""
        loader = GrafanaTemplateLoader()
        
        dashboard = {
            "panels": [
                {
                    "panels": [
                        {
                            "targets": [
                                {
                                    "datasource": {"uid": "old-uid"}
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        result = loader.prepare_for_import(
            dashboard,
            ds_uid="new-uid",
            instance_suffix="host1"
        )
        
        assert result["panels"][0]["panels"][0]["targets"][0]["datasource"]["uid"] == "new-uid"

