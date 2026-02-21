import yaml
import os
from typing import Dict, Any, Optional


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

    def _get_container_ip(self, container_info: Dict[str, Any]) -> Optional[str]:
        """
        Извлекает IP адрес контейнера
        Если IP нет (контейнер остановлен), возвращает None
        """
        network_settings = container_info.get('NetworkSettings', {})
        if network_settings.get('IPAddress'):
            return network_settings['IPAddress']
        networks = network_settings.get('Networks', {})
        if networks:
            first_network = next(iter(networks.values()))
            ip = first_network.get('IPAddress')
            if ip:
                return ip

        return None
    
    def _get_container_target(self, container_info: Dict[str, Any], container_name: str) -> str:
        """
        Получает целевой адрес для подключения к контейнеру.
        Приоритет: IP адрес > имя сервиса из labels > имя контейнера
        """
        # Пробуем получить IP адрес
        ip_address = self._get_container_ip(container_info)
        if ip_address:
            return ip_address
        
        # Если IP нет, используем имя сервиса из Docker Compose labels
        labels = container_info.get('Config', {}).get('Labels', {})
        service_name = labels.get('com.docker.compose.service')
        if service_name:
            return service_name
        
        # Используем имя контейнера (без префикса /)
        return container_name.lstrip('/')

    def _get_host_port(self, container_info: Dict[str, Any]) -> Optional[str]:
        """
        Извлекает хостовой порт контейнера
        """
        host_config = container_info.get('HostConfig', {})
        port_bindings = host_config.get('PortBindings', {})

        if port_bindings:
            for container_port, host_ports in port_bindings.items():
                if host_ports and len(host_ports) > 0:
                    return host_ports[0].get('HostPort')
        return None

    def _build_prometheus_config(
            self,
            container_name: str,
            container_info: Dict[str, Any],
            stack_key: str,
            exporter_config: Dict[str, Any],
            target_address: str
    ) -> Dict[str, Any]:
        """
        Строит конфигурацию Prometheus
        """
        labels = container_info.get('Config', {}).get('Labels', {})
        host_port = self._get_host_port(container_info)

        job_name = f"{container_name}{exporter_config.get('job_name_suffix', '')}"

        static_labels = {
            'container_id': container_info.get('Id', '')[:12],
            'container_name': container_name,
            'stack': stack_key,
            'service': labels.get('com.docker.compose.service', 'unknown'),
            'project': labels.get('com.docker.compose.project', 'unknown'),
            'exporter_image': exporter_config.get('exporter_image', 'unknown')
        }

        if host_port:
            static_labels['host_port'] = host_port

        prometheus_config = {
            'global': {
                'scrape_interval': '15s',
                'evaluation_interval': '15s',
                'external_labels': {
                    'monitor': 'docker-container-monitor'
                }
            },
            'scrape_configs': [
                {
                    'job_name': job_name,
                    'scrape_interval': '15s',
                    'scrape_timeout': '10s',
                    'metrics_path': exporter_config.get('metrics_path', '/metrics'),
                    'static_configs': [
                        {
                            'targets': [f"{target_address}:{exporter_config.get('exporter_port', 9090)}"],
                            'labels': static_labels
                        }
                    ],
                    'relabel_configs': [
                        {
                            'source_labels': ['__address__'],
                            'target_label': 'instance',
                            'replacement': container_name
                        },
                        {
                            'source_labels': ['__meta_docker_container_name'],
                            'regex': '/(.*)',
                            'target_label': 'container_name'
                        }
                    ]
                }
            ],
            'exporter_info': {
                'container_name': container_name,
                'stack': stack_key,
                'exporter_image': exporter_config.get('exporter_image', 'unknown'),
                'exporter_port': exporter_config.get('exporter_port', 9090),
                'target_address': target_address,
                'job_name': job_name
            }
        }

        return prometheus_config

    def generate_config(self, container_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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

        # Получаем целевой адрес для подключения (IP, имя сервиса или имя контейнера)
        target_address = self._get_container_target(container_info, container_name)
        if not target_address:
            print(f"Не удалось определить целевой адрес для контейнера {container_name}")
            return None

        # Строим конфигурацию
        return self._build_prometheus_config(
            container_name=container_name,
            container_info=container_info,
            stack_key=stack_key,
            exporter_config=exporter_config,
            target_address=target_address
        )

    def save_config(self, config: Dict[str, Any], filename: str = 'prometheus.yml') -> None:
        """
        Сохраняет конфигурацию Prometheus в YAML файл
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            print(f"Конфигурация сохранена в {filename}")
        except Exception as e:
            print(f"Ошибка при сохранении конфигурации: {e}")

    def get_exporter_info(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Извлекает информацию об экспортере из конфигурации
        """
        return config.get('exporter_info')
