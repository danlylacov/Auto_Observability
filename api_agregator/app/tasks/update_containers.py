import os
import requests
from dotenv import load_dotenv


class UpdateContainersTask:
    def __init__(self, hosts: list = None):
        load_dotenv()
        self.hosts = hosts
        self.docker_api_url = os.getenv('DOCKER_API_URL')
        self.docker_classification_api_url = os.getenv('DOCKER_CLASSIFICATION_API_URL')

    def _get_host_containers(self, host: dict[str, str] = None) -> list[dict[str, str]]:
        result = []
        containers_url = f'{self.docker_api_url}/api/v1/discover/'
        host_params = {
            "address": host['address'],
            "username": host['username']
        } if host else None
        containers = requests.post(containers_url, params=host_params).json()['containers']
        for container in containers:
            classification = self._classificate_container(container)
            result.append({'info': container, 'classification': classification})
        print(result)
        return result

    def _classificate_container(self, container: dict[str, str] = None) -> dict[str, str]:
        classificate_url = f'{self.docker_classification_api_url}/api/v1/classificate/'
        container_params = {
            "labels": container['Config']['Labels'],
            "envs": container['Config']['Env'],
            "image": container['Config']['Image'],
            "ports": [
                port.split('/')[0] for port in container['Config']['ExposedPorts'].keys()
            ] if 'ExposedPorts' in container['Config'].keys() else []
        }
        classificate_response = requests.post(classificate_url, json=container_params).json()['result']
        return classificate_response


a = UpdateContainersTask()
a._get_host_containers()
