import os
import requests
from dotenv import load_dotenv
from app.db.redis.docker_containers import DockerContainers

from app.services.api_getaway import APIGateway


class UpdateContainers:
    """
    Сервисный класс для обновления информации о контейнерах
    """

    def __init__(self, hosts: list = None):
        self.hosts = hosts

        load_dotenv()
        self.docker_api_url = os.getenv('DOCKER_API_URL')
        self.docker_classification_api_url = os.getenv('DOCKER_CLASSIFICATION_API_URL')
        self.docker_api = APIGateway(self.docker_api_url)
        self.docker_classification_api = APIGateway(self.docker_classification_api_url)

    def _get_host_containers(self, host: dict[str, str] = None) -> dict:
        """
        Получение всех контейнеров по хосту
        """
        result = {}
        host_params = {
            "address": host['address'],
            "username": host['username']
        } if host else None

        containers = self.docker_api.make_request(method="POST", endpoint='/api/v1/discover/', params=host_params)['containers']

        for container in containers:
            classification = self._classificate_container(container)
            result[container['Id']] = {'info': container, 'classification': classification}
        return result

    def _classificate_container(self, container: dict[str, str] = None) -> dict[str, str]:
        """
        Классификация контейнера (определение технологий) по информации о нем
        """
        container_params = {
            "labels": container['Config']['Labels'],
            "envs": container['Config']['Env'],
            "image": container['Config']['Image'],
            "ports": [
                port.split('/')[0] for port in container['Config']['ExposedPorts'].keys()
            ] if 'ExposedPorts' in container['Config'].keys() else []
        }
        classificate_response = self.docker_classification_api.make_request(
            method="POST",
            endpoint='/api/v1/classificate/',
            json_data=container_params
        )
        return classificate_response

    def upload_containers(self) -> None:
        """
        Обновление информации о контейнерах в Redis
        """
        hosts = self.hosts if self.hosts else [None]
        for host in hosts:
            containers = self._get_host_containers(host)
            docker_containers = DockerContainers()
            docker_containers.delete_all_containers_by_host(host if host else 'localhost')
            docker_containers.upload_containers(containers, host if host else 'localhost')
