import sys
from pathlib import Path


# Добавляем корень репозитория в sys.path, чтобы импортировать пакеты сервисов
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Также добавляем директории сервисов как пакеты верхнего уровня,
# чтобы импорты вида `from app...` корректно резолвились внутри них.
SERVICE_DIRS = [
    ROOT_DIR / "api_agregator",
    ROOT_DIR / "docker_api",
    ROOT_DIR / "docker_classification",
    ROOT_DIR / "prometheus_generation",
    ROOT_DIR / "prometheus_manager",
    ROOT_DIR / "grafana_generation",
    ROOT_DIR / "grafana_manager",
]

for service_path in SERVICE_DIRS:
    if service_path.is_dir():
        if str(service_path) not in sys.path:
            sys.path.insert(0, str(service_path))

# Специальный алиас: внутри api_agregator используются импорты вида `from app...`
# При тестировании создаём модуль `app`, указывающий на `api_agregator.app`.
try:
    import api_agregator.app as _api_app

    sys.modules.setdefault("app", _api_app)
except Exception:
    # В контекстах, где пакет ещё недоступен, просто пропускаем;
    # конкретные тесты всё равно упадут при импорте, если это критично.
    pass



