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

        Определяет путь к файлу signatures.yml в корне проекта.
        """
        if os.path.exists('/app/signatures.yml'):
            self.signatures_path = '/app/signatures.yml'
        else:
            current_file = os.path.abspath(__file__)
            current_dir = os.path.dirname(current_file)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            signatures_path = os.path.join(project_root, 'signatures.yml')
            
            if not os.path.exists(signatures_path):
                cwd = os.getcwd()
                if os.path.basename(cwd) == 'prometheus_generation':
                    project_root = os.path.dirname(cwd)
                    signatures_path = os.path.join(project_root, 'signatures.yml')
                if not os.path.exists(signatures_path):
                    test_paths = [
                        os.path.join(cwd, 'signatures.yml'),
                        os.path.join(os.path.dirname(cwd), 'signatures.yml'),
                        os.path.join(os.path.dirname(os.path.dirname(cwd)), 'signatures.yml'),
                    ]
                    for test_path in test_paths:
                        if os.path.exists(test_path):
                            signatures_path = test_path
                            break
            
            self.signatures_path = signatures_path

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
