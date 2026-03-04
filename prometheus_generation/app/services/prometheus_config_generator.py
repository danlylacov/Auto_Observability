import yaml
import os
from typing import Dict, Any, Optional
from app.services.exporter_env_generator import ExporterEnvGenerator


class PrometheusConfigGenerator:
    """
    Класс для генерации конфигурации Prometheus на основе данных Docker контейнера
    """

    def __init__(self, signatures_path: Optional[str] = None):
        if signatures_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            signatures_path = os.path.join(current_dir, 'signatures.yml')

        self.signatures_path = signatures_path
        self.exporter_configs = self._load_signatures()
        self.env_generator = ExporterEnvGenerator(signatures_path)

    def _load_signatures(self) -> Dict[str, Any]:
        """
        Загружает конфигурации экспортеров из файла signatures.yml
        """
        try:
            with open(self.signatures_path, 'r', encoding='utf-8') as f:
                signatures = yaml.safe_load(f)
            return signatures or {}
        except FileNotFoundError:
            print(f"Файл signatures.yml не найден по пути: {self.signatures_path}")
            return {}
        except yaml.YAMLError as e:
            print(f"Ошибка при парсинге YAML файла: {e}")
            return {}

    def _get_container_name(self, container_info: Dict[str, Any]) -> str:
        """
        Извлекает имя контейнера из информации о контейнере
        """
        container_name = container_info.get('Name', '').lstrip('/')
        if not container_name:
            container_name = container_info.get('Config', {}).get('Hostname', 'unknown')
        return container_name

    def _get_stack_from_classification(self, classification: Dict[str, Any]) -> Optional[str]:
        """
        Извлекает стек из результатов классификации
        """
        result = classification.get('result', [])
        if result and len(result) > 0:
            return result[0][0]
        return None

    def _normalize_stack_name(self, stack: str) -> str:
        """
        Нормализует название стека для поиска в конфигурациях
        """
        return stack.lower().replace(' ', '_')

    def _build_prometheus_config(
            self,
            container_name: str,
            container_info: Dict[str, Any],
            exporter_config: Dict[str, Any],
            target_address: str
    ) -> Dict[str, Any]:
        """
        Строит конфигурацию Prometheus
        """
        labels = container_info.get('Config', {}).get('Labels', {})

        job_name = f"{container_name}{exporter_config.get('job_name_suffix', '')}"

        scrape_config = {
            'job_name': job_name,
            'scrape_interval': '15s',
            'scrape_timeout': '10s',
            'file_sd_configs': {
                'files': [f'targets/{job_name}.yml']  # Должен быть список, а не словарь!
            }
        }

        target_yml = {
            'targets': [f'{target_address}:{self.env_generator.get_exporter_port()[0]}'],  # Статический IP!
            'labels': labels
        }

        prometheus_config = {
            'scrape_config': scrape_config,
            f'targets/{job_name}.yml': target_yml
        }

        return prometheus_config

    def get_container_network(self, container_info: Dict[str, Any]) -> Optional[str]:
        """
        Извлекает имя сети контейнера
        """
        return self.env_generator.get_container_network(container_info)

    def generate_config(self, container_data: Dict[str, Any], target_address: str) -> Optional[Dict[str, Any]]:
        """
        Генерирует конфигурацию Prometheus на основе данных Docker контейнера
        """
        container_info = container_data.get('info', {})
        classification = container_data.get('classification', {})

        # Получаем имя контейнера
        container_name = self._get_container_name(container_info)

        # Получаем стек из классификации
        stack = self._get_stack_from_classification(classification)
        if not stack:
            print(f"Не удалось определить стек для контейнера {container_name}")
            return None

        # Нормализуем название стека
        stack_key = self._normalize_stack_name(stack)

        # Проверяем наличие конфигурации для стека
        if stack_key not in self.exporter_configs:
            print(f"Нет готовой конфигурации для стека: {stack} (ключ: {stack_key})")
            return None

        exporter_config = self.exporter_configs[stack_key]

        # Получаем сеть контейнера
        network_name = self.get_container_network(container_info)

        # Строим конфигурацию
        config = self._build_prometheus_config(
            container_name=container_name,
            container_info=container_info,
            exporter_config=exporter_config,
            target_address=target_address
        )

        result = {
            'config': config,
            'exporter_config': exporter_config
        }
        # Добавляем информацию о сети и env переменных в exporter_info
        result['exporter_config']['network'] = network_name

        return result
