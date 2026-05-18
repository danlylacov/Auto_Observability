import json
import logging
import os
import time
from typing import Any, Dict, Optional, Union

import docker
import yaml

from app.services.exporter_env_generator import ExporterEnvGenerator

logger = logging.getLogger(__name__)


class PrometheusConfigGenerator:
    """
    Класс для генерации конфигурации Prometheus на основе данных Docker контейнера.

    Предоставляет методы для создания конфигураций Prometheus для различных стеков технологий.
    """

    def __init__(self, signatures_path: Optional[str] = None):
        """
        Инициализация генератора конфигураций Prometheus.

        Args:
            signatures_path: Путь к файлу signatures.yml. Если None, используется файл в корне проекта.
        """
        if signatures_path is None:
            if os.path.exists('/app/signatures.yml'):
                signatures_path = '/app/signatures.yml'
            else:
                current_file = os.path.abspath(__file__)
                # /app/app/services/<file>.py -> /app
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
                signatures_path = os.path.join(project_root, 'signatures.yml')

        self.signatures_path = signatures_path
        self.exporter_configs = self._load_signatures()
        self.env_generator = ExporterEnvGenerator(signatures_path)

    def _load_signatures(self) -> Dict[str, Any]:
        """
        Загружает конфигурации экспортеров из файла signatures.yml.

        Returns:
            Dict[str, Any]: Словарь с конфигурациями экспортеров
        """
        try:
            with open(self.signatures_path, 'r', encoding='utf-8') as f:
                signatures = yaml.safe_load(f)
            return signatures or {}
        except FileNotFoundError:
            logger.error(f"Файл signatures.yml не найден по пути: {self.signatures_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Ошибка при парсинге YAML файла: {e}")
            return {}

    def _get_container_name(self, container_info: Dict[str, Any]) -> str:
        """
        Извлекает имя контейнера из информации о контейнере.

        Args:
            container_info: Информация о контейнере

        Returns:
            str: Имя контейнера
        """
        container_name = container_info.get('Name', '').lstrip('/')
        if not container_name:
            container_name = container_info.get('Config', {}).get('Hostname', 'unknown')
        return container_name

    def _get_stack_from_classification(self, classification: Dict[str, Any]) -> Optional[str]:
        """
        Извлекает стек из результатов классификации.

        Args:
            classification: Результаты классификации контейнера

        Returns:
            Optional[str]: Название стека или None
        """
        result = classification.get('result', [])
        if result and len(result) > 0:
            return result[0][0]
        return None

    @staticmethod
    def _host_port_from_port_bindings(
        info: dict[str, Any],
        preferred_internal: int | None,
    ) -> int | None:
        bindings = (info.get("HostConfig") or {}).get("PortBindings") or {}
        if preferred_internal is not None:
            pk = f"{int(preferred_internal)}/tcp"
            lst = bindings.get(pk)
            if lst and isinstance(lst, list) and lst[0].get("HostPort"):
                hp = lst[0]["HostPort"]
                if hp:
                    return int(hp)
        for _pk, lst in bindings.items():
            if str(_pk).endswith("/tcp") and lst and isinstance(lst, list) and lst[0].get("HostPort"):
                hp = lst[0]["HostPort"]
                if hp:
                    return int(hp)
        return None

    @classmethod
    def _published_host_port(
        cls,
        container_info: dict[str, Any],
        preferred_internal: int | None,
    ) -> int | None:
        """Host port опубликованный для internal TCP-порта workload (из docker inspect)."""
        info = container_info
        ports = (info.get("NetworkSettings") or {}).get("Ports") or {}
        if preferred_internal is not None:
            pk = f"{int(preferred_internal)}/tcp"
            b = ports.get(pk)
            if b and isinstance(b, list) and b[0].get("HostPort"):
                return int(b[0]["HostPort"])
        for _pk, b in ports.items():
            if str(_pk).endswith("/tcp") and b and isinstance(b, list) and b[0].get("HostPort"):
                return int(b[0]["HostPort"])
        return cls._host_port_from_port_bindings(info, preferred_internal)

    @staticmethod
    def _scraping_timing(value: Optional[Union[int, float, str]], default: str) -> str:
        """Prometheus duration string from signatures.yml (int/float interpreted as seconds)."""
        if value is None or value == "":
            return default
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            if isinstance(value, float) and value != int(value):
                return f"{value}s"
            return f"{int(value)}s"
        parsed = str(value).strip()
        return parsed if parsed else default

    def _normalize_stack_name(self, stack: str) -> str:
        """
        Нормализует название стека для поиска в конфигурациях.

        Args:
            stack: Название стека

        Returns:
            str: Нормализованное название стека
        """
        return stack.lower().replace(' ', '_')

    def _apply_sidecar_runtime(
        self,
        stack_key: str,
        container_info: Dict[str, Any],
        network_name: Optional[str],
        exporter_config: Dict[str, Any],
        generated_env_vars: Dict[str, str],
    ) -> None:
        """
        Правит command/env/entrypoint sidecar-экспортёра под реальные образы (mysqld 0.15, ES exporter, Telegraf и т.д.).
        """
        from urllib.parse import quote

        eg = self.env_generator
        cname = eg._get_container_name(container_info)
        env_list = container_info.get("Config", {}).get("Env", [])
        env_dict = eg._parse_env_vars(env_list)
        target = eg._get_container_target(container_info, cname, network_name)

        if stack_key == "rabbitmq" and exporter_config.get("native_prometheus_scrape"):
            exporter_config["env_vars"] = {}
            exporter_config["exporter_command"] = None
            exporter_config.pop("exporter_entrypoint", None)
            return

        if stack_key in ("mysql", "mariadb"):
            cport = eg._extract_port_from_exposed(container_info, eg._get_default_port(stack_key))
            creds = eg._get_credentials(env_dict, stack_key)
            user = creds.get("user") or "root"
            pw = creds.get("password") or ""
            exporter_config["exporter_command"] = [
                f"--mysqld.address={target}:{cport}",
                f"--mysqld.username={user}",
            ]
            exporter_config["env_vars"] = {"MYSQLD_EXPORTER_PASSWORD": pw}
            exporter_config.pop("exporter_entrypoint", None)
            return

        if stack_key == "elasticsearch":
            cport = eg._extract_port_from_exposed(container_info, eg._get_default_port(stack_key))
            uri = f"http://{target}:{cport}"
            exporter_config["exporter_command"] = [
                f"--es.uri={uri}",
                "--es.ssl-skip-verify",
            ]
            exporter_config["env_vars"] = {}
            exporter_config.pop("exporter_entrypoint", None)
            return

        if stack_key == "opensearch":
            cport = eg._extract_port_from_exposed(container_info, eg._get_default_port(stack_key))
            creds = eg._get_credentials(env_dict, stack_key)
            user = creds.get("user") or "admin"
            pw = creds.get("password") or ""
            if pw:
                uq = quote(str(user), safe="")
                pq = quote(str(pw), safe="")
                uri = f"http://{uq}:{pq}@{target}:{cport}"
            else:
                uri = f"http://{target}:{cport}"
            exporter_config["exporter_command"] = [
                f"--es.uri={uri}",
                "--es.ssl-skip-verify",
            ]
            exporter_config["env_vars"] = {}
            exporter_config.pop("exporter_entrypoint", None)
            return

        if stack_key == "clickhouse":
            cport = eg._extract_port_from_exposed(container_info, eg._get_default_port(stack_key))
            exporter_config["exporter_command"] = [
                f"-scrape_uri=http://default@{target}:{cport}/",
            ]
            exporter_config["env_vars"] = generated_env_vars or {}
            exporter_config.pop("exporter_entrypoint", None)
            return

        if stack_key == "kafka":
            cport = eg._extract_port_from_exposed(container_info, eg._get_default_port(stack_key))
            exporter_config["exporter_command"] = [
                f"--kafka.server={target}:{cport}",
            ]
            exporter_config["env_vars"] = generated_env_vars or {}
            exporter_config.pop("exporter_entrypoint", None)
            return

        if stack_key == "nats":
            uri = f"http://{target}:8222"
            exporter_config["exporter_command"] = ["-varz", uri]
            exporter_config["env_vars"] = generated_env_vars or {}
            exporter_config.pop("exporter_entrypoint", None)
            return

        if stack_key == "influxdb":
            cport = eg._extract_port_from_exposed(container_info, eg._get_default_port(stack_key))
            influx_uri = f"http://{target}:{cport}"
            script = (
                f'printf "%s\\n" "[[inputs.influxdb]]" "  urls = [\\"{influx_uri}\\"]" "" '
                '"[[outputs.prometheus_client]]" "  listen = \\":9122\\"" "  path = \\"/metrics\\"" '
                "> /tmp/tg.conf && exec telegraf --config /tmp/tg.conf"
            )
            exporter_config["exporter_entrypoint"] = ["/bin/sh", "-c", script]
            exporter_config["exporter_command"] = None
            exporter_config["env_vars"] = {}
            return

        exporter_config["env_vars"] = generated_env_vars or {}
        exporter_config.pop("exporter_entrypoint", None)

    def _get_exporter_host_port(self, container_port: str) -> Optional[str]:
        """
        Получает внешний порт экспортера на хосте.
        Убирает выбор порта - всегда использует первый найденный внешний порт экспортера.

        Args:
            container_port: Внутренний порт контейнера (игнорируется, используется для логирования)

        Returns:
            Optional[str]: Внешний порт на хосте или None, если не найден
        """
        try:
            docker_client = docker.from_env()
            for container in docker_client.containers.list(all=True):
                if 'exporter' in container.name.lower():
                    ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                    for internal_port, port_bindings in ports.items():
                        if port_bindings and len(port_bindings) > 0:
                            host_port = port_bindings[0].get('HostPort')
                            if host_port:
                                return host_port
        except Exception as e:
            pass

    def _build_prometheus_config(
            self,
            container_name: str,
            container_info: Dict[str, Any],
            exporter_config: Dict[str, Any],
            target_address: str
    ) -> Dict[str, Any]:
        """
        Строит конфигурацию Prometheus.

        Args:
            container_name: Имя контейнера
            container_info: Информация о контейнере
            exporter_config: Конфигурация экспортера
            target_address: Адрес целевого контейнера

        Returns:
            Dict[str, Any]: Конфигурация Prometheus
        """
        labels = container_info.get('Config', {}).get('Labels', {})

        job_name = f"{container_name}{exporter_config.get('job_name_suffix', '')}"

        scrape_interval = self._scraping_timing(
            exporter_config.get('scrape_interval'), '15s'
        )
        scrape_timeout = self._scraping_timing(
            exporter_config.get('scrape_timeout'), '30s'
        )

        scrape_config = {
            'job_name': job_name,
            'scrape_interval': scrape_interval,
            'scrape_timeout': scrape_timeout,
            'file_sd_configs': [
                {
                    'files': [f'targets/{job_name}.yml']
                }
            ]
        }

        scrape_port = exporter_config.get("prometheus_scrape_port")
        if scrape_port is None:
            scrape_port = exporter_config.get("exporter_port", "9187")
        scrape_port = str(scrape_port).strip()

        target_yml = {
            'targets': [f'{target_address}:{scrape_port}'],
            'labels': labels
        }

        prometheus_config = {
            'scrape_config': scrape_config,
            f'target': target_yml
        }

        return prometheus_config

    def get_container_network(self, container_info: Dict[str, Any]) -> Optional[str]:
        """
        Извлекает имя сети контейнера.

        Args:
            container_info: Информация о контейнере

        Returns:
            Optional[str]: Имя сети или None
        """
        return self.env_generator.get_container_network(container_info)

    def generate_config(self, container_data: Dict[str, Any], target_address: str) -> Optional[Dict[str, Any]]:
        """
        Генерирует конфигурацию Prometheus на основе данных Docker контейнера.

        Args:
            container_data: Данные о контейнере (info и classification)
            target_address: Адрес целевого контейнера

        Returns:
            Optional[Dict[str, Any]]: Конфигурация Prometheus или None при ошибке
        """
        container_info = container_data.get('info', {})
        classification = container_data.get('classification', {})

        container_name = self._get_container_name(container_info)

        stack = self._get_stack_from_classification(classification)
        if not stack:
            return None

        stack_key = self._normalize_stack_name(stack)

        if stack_key not in self.exporter_configs:
            return None

        exporter_config = dict(self.exporter_configs[stack_key])
        for _k in ("grafana_dashboard_id", "dashboard_id"):
            exporter_config.pop(_k, None)
        scrape_override = container_data.get("prometheus_scrape_port")
        if scrape_override is not None:
            exporter_config["prometheus_scrape_port"] = int(scrape_override)

        network_name = self.get_container_network(container_info)

        if stack_key == "rabbitmq" and exporter_config.get("native_prometheus_scrape"):
            generated_env_vars: dict[str, str] = {}
        else:
            generated_env_vars = self.env_generator.generate_env_vars(
                container_info=container_info,
                stack_key=stack_key,
                network_name=network_name,
            )

        self._apply_sidecar_runtime(
            stack_key, container_info, network_name, exporter_config, generated_env_vars
        )

        if exporter_config.get("native_prometheus_scrape"):
            int_port = exporter_config.get("exporter_port")
            try:
                pint = int(int_port) if int_port is not None else None
            except (TypeError, ValueError):
                pint = None
            pub = self._published_host_port(container_info, pint) if pint is not None else None
            # #region agent log
            try:
                dbg_path = (
                    "/home/daniil/Рабочий стол/диплом/Auto_Observability/.cursor/debug-a72628.log"
                )
                with open(dbg_path, "a", encoding="utf-8") as _df:
                    _df.write(
                        json.dumps(
                            {
                                "sessionId": "a72628",
                                "hypothesisId": "H1",
                                "location": "prometheus_config_generator:generate_config:native_port",
                                "message": "native_prometheus scrape port resolution",
                                "data": {
                                    "container": container_name,
                                    "internal_port": pint,
                                    "published_host_port": pub,
                                    "had_scrape_override": scrape_override is not None,
                                },
                                "timestamp": int(time.time() * 1000),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            except OSError:
                pass
            # #endregion
            if pub is not None and exporter_config.get("prometheus_scrape_port") is None:
                exporter_config["prometheus_scrape_port"] = pub

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

        result['exporter_config']['network'] = network_name

        return result
