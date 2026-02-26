import yaml
import os
from typing import Dict, Any, Optional


class ExporterEnvGenerator:
    """
    Универсальный класс для генерации переменных окружения экспортера
    на основе типа стека и информации о целевом контейнере
    """
    
    def __init__(self, signatures_path: Optional[str] = None):
        if signatures_path is None:
            # Теперь signatures.yml находится в той же директории
            current_dir = os.path.dirname(os.path.abspath(__file__))
            signatures_path = os.path.join(current_dir, 'signatures.yml')
        
        self.signatures_path = signatures_path
        self.exporter_configs = self._load_signatures()
    
    def _load_signatures(self) -> Dict[str, Any]:
        """Загружает конфигурации экспортеров из signatures.yml"""
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
    
    def _parse_env_vars(self, env_list: list) -> Dict[str, str]:
        """Парсит список env переменных в словарь"""
        env_dict = {}
        for env_var in env_list:
            if '=' in env_var:
                key, value = env_var.split('=', 1)
                env_dict[key] = value
        return env_dict
    
    def _get_container_name(self, container_info: Dict[str, Any]) -> str:
        """Извлекает имя контейнера"""
        container_name = container_info.get('Name', '').lstrip('/')
        if not container_name:
            container_name = container_info.get('Config', {}).get('Hostname', 'unknown')
        return container_name
    
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
    
    def _get_default_port(self, stack_key: str) -> str:
        """Возвращает дефолтный порт для стека"""
        default_ports = {
            'postgresql': '5432',
            'timescaledb': '5432',
            'mysql': '3306',
            'mariadb': '3306',
            'mongodb': '27017',
            'redis': '6379',
            'cassandra': '9042',
            'clickhouse': '8123',
            'couchdb': '5984',
            'influxdb': '8086',
            'neo4j': '7474',
            'rabbitmq': '5672',
            'kafka': '9092',
            'nats': '4222',
            'elasticsearch': '9200',
            'opensearch': '9200',
        }
        return default_ports.get(stack_key, '8080')
    
    def _extract_port_from_exposed(self, container_info: Dict[str, Any], default_port: str) -> str:
        """Извлекает порт из ExposedPorts контейнера"""
        exposed_ports = container_info.get('Config', {}).get('ExposedPorts', {})
        if exposed_ports:
            for port_key in exposed_ports.keys():
                port_num = port_key.split('/')[0]
                if port_num == default_port:
                    return port_num
            first_port = list(exposed_ports.keys())[0].split('/')[0]
            return first_port

        network_settings = container_info.get('NetworkSettings', {})
        port_bindings = network_settings.get('Ports', {})
        if port_bindings:
            for port_key in port_bindings.keys():
                port_num = port_key.split('/')[0]
                if port_num == default_port:
                    return port_num
            first_port = list(port_bindings.keys())[0].split('/')[0]
            return first_port
        
        return default_port
    
    def _get_container_target(self, container_info: Dict[str, Any], container_name: str, network_name: Optional[str] = None) -> str:
        """
        Получает целевой адрес для подключения к контейнеру.
        Приоритет: IP адрес (для bridge сети) > имя сервиса из labels > имя контейнера
        """
        if network_name == 'bridge':
            ip_address = self._get_container_ip(container_info)
            if ip_address:
                return ip_address

        labels = container_info.get('Config', {}).get('Labels', {})
        service_name = labels.get('com.docker.compose.service')
        if service_name:
            return service_name

        return container_name.lstrip('/')
    
    def _get_credentials(self, env_dict: Dict[str, str], stack_key: str) -> Dict[str, str]:
        """Извлекает credentials из env переменных на основе типа стека"""
        credentials = {}

        if stack_key in ['postgresql', 'timescaledb']:
            credentials['user'] = env_dict.get('POSTGRES_USER', env_dict.get('PGUSER', 'postgres'))
            credentials['password'] = env_dict.get('POSTGRES_PASSWORD', env_dict.get('PGPASSWORD', 'postgres'))
            credentials['database'] = env_dict.get('POSTGRES_DB', env_dict.get('PGDATABASE', 'postgres'))

        elif stack_key in ['mysql', 'mariadb']:
            credentials['user'] = env_dict.get('MYSQL_USER', env_dict.get('MARIADB_USER', 'root'))
            credentials['password'] = env_dict.get('MYSQL_PASSWORD', env_dict.get('MARIADB_PASSWORD', 'password'))
            credentials['database'] = env_dict.get('MYSQL_DATABASE', env_dict.get('MARIADB_DATABASE', ''))

        elif stack_key == 'mongodb':
            # MongoDB может использовать MONGO_INITDB_ROOT_USERNAME и MONGO_INITDB_ROOT_PASSWORD
            credentials['user'] = env_dict.get('MONGO_INITDB_ROOT_USERNAME', env_dict.get('MONGO_USER', ''))
            credentials['password'] = env_dict.get('MONGO_INITDB_ROOT_PASSWORD', env_dict.get('MONGO_PASSWORD', ''))
            credentials['database'] = env_dict.get('MONGO_INITDB_DATABASE', env_dict.get('MONGO_DB', ''))

        elif stack_key == 'redis':
            credentials['password'] = env_dict.get('REDIS_PASSWORD', '')

        elif stack_key == 'influxdb':
            credentials['user'] = env_dict.get('INFLUXDB_USER', 'admin')
            credentials['password'] = env_dict.get('INFLUXDB_PASSWORD', 'admin')
            credentials['database'] = env_dict.get('INFLUXDB_DB', '')

        elif stack_key == 'clickhouse':
            credentials['user'] = env_dict.get('CLICKHOUSE_USER', 'default')
            credentials['password'] = env_dict.get('CLICKHOUSE_PASSWORD', '')
            credentials['database'] = env_dict.get('CLICKHOUSE_DB', 'default')

        elif stack_key in ['elasticsearch', 'opensearch']:
            credentials['user'] = env_dict.get('ELASTICSEARCH_USERNAME', env_dict.get('OPENSEARCH_USERNAME', ''))
            credentials['password'] = env_dict.get('ELASTICSEARCH_PASSWORD', env_dict.get('OPENSEARCH_PASSWORD', ''))

        elif stack_key == 'rabbitmq':
            credentials['user'] = env_dict.get('RABBITMQ_DEFAULT_USER', 'guest')
            credentials['password'] = env_dict.get('RABBITMQ_DEFAULT_PASS', 'guest')

        elif stack_key == 'kafka':
            credentials['user'] = env_dict.get('KAFKA_SASL_USERNAME', '')
            credentials['password'] = env_dict.get('KAFKA_SASL_PASSWORD', '')
        
        return credentials
    
    def _format_connection_string(self, template: str, host: str, port: str, credentials: Dict[str, str]) -> str:
        """Форматирует строку подключения по шаблону"""
        try:
            if '{user}' not in template and '{password}' not in template and '{database}' not in template:
                return template.format(host=host, port=port)

            user = credentials.get('user', '')
            password = credentials.get('password', '')
            database = credentials.get('database', '')

            result = template.format(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )

            if not database and '/{database}' in template:
                result = result.replace(f'/{database}', '/')
            
            return result
        except KeyError as e:
            print(f"Ошибка форматирования шаблона: {e}")
            return template
        except Exception as e:
            print(f"Неожиданная ошибка при форматировании шаблона: {e}")
            return template
    
    def generate_env_vars(
        self, 
        container_info: Dict[str, Any], 
        stack_key: str,
        network_name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Генерирует переменные окружения для экспортера на основе типа стека
        и информации о целевом контейнере
        """
        if stack_key not in self.exporter_configs:
            return {}
        
        exporter_config = self.exporter_configs[stack_key]
        env_vars_config = exporter_config.get('env_vars', {})

        if not env_vars_config:
            return {}

        container_name = self._get_container_name(container_info)
        env_list = container_info.get('Config', {}).get('Env', [])
        env_dict = self._parse_env_vars(env_list)

        target_address = self._get_container_target(container_info, container_name, network_name)

        default_port = self._get_default_port(stack_key)
        container_port = self._extract_port_from_exposed(container_info, default_port)

        credentials = self._get_credentials(env_dict, stack_key)

        generated_env = {}
        
        for env_key, env_value in env_vars_config.items():
            env_template = exporter_config.get('env_template')
            if env_template and env_key in env_vars_config:
                connection_string = self._format_connection_string(
                    env_template,
                    target_address,
                    container_port,
                    credentials
                )
                generated_env[env_key] = connection_string
            else:
                if '{host}' in env_value:
                    generated_env[env_key] = env_value.replace('{host}', target_address)
                elif '{port}' in env_value:
                    generated_env[env_key] = env_value.replace('{port}', container_port)
                else:
                    generated_env[env_key] = env_value
        
        return generated_env
    
    def get_container_network(self, container_info: Dict[str, Any]) -> Optional[str]:
        """Извлекает имя сети контейнера"""
        network_settings = container_info.get('NetworkSettings', {})
        networks = network_settings.get('Networks', {})
        
        if not networks:
            return None
        network_names = list(networks.keys())

        if 'bridge' in network_names:
            return 'bridge'
        
        return network_names[0]

