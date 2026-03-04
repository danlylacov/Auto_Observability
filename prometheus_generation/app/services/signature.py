import os


class Signature:
    """
    Класс для управления signatures.yml (настройка генерации Prometheus config)
    """

    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.signatures_path = os.path.join(current_dir, 'signatures.yml')

    def get(self) -> str:
        """
        Получение текущего файла
        """
        with open(self.signatures_path) as f: return f.read()

    def update(self, signature: str):
        """
        Обновление файла
        """
        with open(self.signatures_path, 'w') as f: f.write(signature)
