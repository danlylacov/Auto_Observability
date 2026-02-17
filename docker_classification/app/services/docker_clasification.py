import yaml
from collections import defaultdict


class WeightedDiscovery:
    def __init__(self, rules_path: str = None) -> None:
        import os
        if rules_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            rules_path = os.path.join(current_dir, 'signatures.yml')
        with open(rules_path, 'r') as f:
            self.rules = yaml.safe_load(f)
        self.threshold = 50

    def classify_container(self, labels: dict, envs: list, image: str, ports: list) -> list:
        """
        Классификация контейнера
        """
        scores = defaultdict(int)

        for port, data in self.rules['ports'].items():
            if port in ports:
                scores[data['tech']] += data['weight']

        for env_key, data in self.rules['env'].items():
            if any(env_key in e for e in envs):
                scores[data['tech']] += data['weight']

        for img_part, data in self.rules['images'].items():
            if img_part in image:
                scores[data['tech']] += data['weight']

        for lb_key, data in self.rules['labels'].items():
            if lb_key in labels:
                tech = labels[lb_key] if data['tech'] == "auto" else data['tech']
                scores[tech] += data['weight']

        final_decision = {t: s for t, s in scores.items() if s >= self.threshold}

        return sorted(final_decision.items(), key=lambda x: x[1], reverse=True)


