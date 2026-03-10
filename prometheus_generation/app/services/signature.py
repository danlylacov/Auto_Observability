import os


class Signature:
    """
    Класс для управления signatures.yml.

    Предоставляет методы для чтения и обновления файла signatures.yml,
    который содержит настройки генерации Prometheus config.
    """

    def __init__(self):
        """
        Инициализация класса Signature.

        Определяет путь к файлу signatures.yml в текущей директории.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.signatures_path = os.path.join(current_dir, 'signatures.yml')

    def get(self) -> str:
        """
        Получение текущего содержимого файла signatures.yml.

        Returns:
            str: Содержимое файла signatures.yml
        """
        with open(self.signatures_path, 'r', encoding='utf-8') as f:
            return f.read()

    def update(self, signature: str):
        """
        Обновление файла signatures.yml.

        Args:
            signature: Новое содержимое файла
        """
        with open(self.signatures_path, 'w', encoding='utf-8') as f:
            f.write(signature)
