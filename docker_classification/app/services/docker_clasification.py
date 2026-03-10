import os
import yaml
from collections import defaultdict


class WeightedDiscovery:
    """
    Класс для классификации Docker контейнеров по технологиям.

    Использует взвешенную систему правил для определения технологий
    на основе портов, переменных окружения, образов и меток.
    """

    def __init__(self, rules_path: str = None) -> None:
        """
        Инициализация WeightedDiscovery.

        Args:
            rules_path: Путь к файлу с правилами классификации.
                       Если None, используется signatures.yml в текущей директории.
        """
        if rules_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            rules_path = os.path.join(current_dir, 'signatures.yml')
        with open(rules_path, 'r', encoding='utf-8') as f:
            self.rules = yaml.safe_load(f)
        self.threshold = 50

    def classify_container(self, labels: dict, envs: list, image: str, ports: list) -> list:
        """
        Классификация контейнера по технологиям.

        Args:
            labels: Словарь с метками контейнера
            envs: Список переменных окружения
            image: Имя образа Docker
            ports: Список портов контейнера

        Returns:
            list: Отсортированный список кортежей (технология, балл)
        """
        scores = defaultdict(int)

        for port, data in self.rules['ports'].items():
            if port in ports:
                scores[data['tech']] += data['weight']

        for env_key, data in self.rules['env'].items():
            if any(env_key in env_var for env_var in envs):
                scores[data['tech']] += data['weight']

        for img_part, data in self.rules['images'].items():
            if img_part in image:
                scores[data['tech']] += data['weight']

        for lb_key, data in self.rules['labels'].items():
            if lb_key in labels:
                tech = labels[lb_key] if data['tech'] == "auto" else data['tech']
                scores[tech] += data['weight']

        final_decision = {tech: score for tech, score in scores.items() if score >= self.threshold}

        return sorted(final_decision.items(), key=lambda x: x[1], reverse=True)


