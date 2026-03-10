#!/usr/bin/env python3
"""
Тестовый скрипт для полного цикла подключения мониторинга контейнера.
Повторяет логику фронтенда: генерация конфигурации -> запуск экспортера -> обновление контейнеров.
"""

import requests
import json
import sys
import time
from typing import Dict, Any, Optional

# Конфигурация API
API_BASE_URL = "http://localhost:8081"
PROMETHEUS_API = f"{API_BASE_URL}/api/v1/prometheus"
CONTAINERS_API = f"{API_BASE_URL}/api/v1/containers"


def log(message: str, level: str = "INFO"):
    """Логирование с цветами"""
    colors = {
        "INFO": "\033[94m",      # Синий
        "SUCCESS": "\033[92m",   # Зеленый
        "ERROR": "\033[91m",     # Красный
        "WARNING": "\033[93m",   # Желтый
        "RESET": "\033[0m"
    }
    print(f"{colors.get(level, '')}[{level}]{colors['RESET']} {message}")


def get_container(container_id: str) -> Optional[Dict[str, Any]]:
    """Получает информацию о контейнере по ID"""
    try:
        response = requests.get(f"{CONTAINERS_API}/containers")
        response.raise_for_status()
        containers = response.json()
        return containers.get(container_id)
    except requests.exceptions.RequestException as e:
        log(f"Ошибка при получении контейнера: {e}", "ERROR")
        if hasattr(e, 'response') and e.response is not None:
            log(f"Детали: {e.response.text}", "ERROR")
        return None


def generate_config(container_id: str, host_id: str) -> Optional[Dict[str, Any]]:
    """Генерирует конфигурацию Prometheus для контейнера"""
    try:
        log(f"Генерация конфигурации для контейнера {container_id[:12]}...", "INFO")
        response = requests.post(
            f"{PROMETHEUS_API}/generate_config",
            params={"container_id": container_id, "host_id": host_id}
        )
        response.raise_for_status()
        result = response.json()
        log(f"Конфигурация сгенерирована успешно (config_id: {result.get('config_id')})", "SUCCESS")
        return result
    except requests.exceptions.RequestException as e:
        log(f"Ошибка при генерации конфигурации: {e}", "ERROR")
        if hasattr(e, 'response') and e.response is not None:
            log(f"Детали: {e.response.text}", "ERROR")
        return None


def start_exporter(container_id: str, port: int) -> Optional[Dict[str, Any]]:
    """Запускает экспортер для контейнера"""
    try:
        log(f"Запуск экспортера на порту {port}...", "INFO")
        response = requests.post(
            f"{PROMETHEUS_API}/up_exporter",
            params={"container_id": container_id, "port": port}
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("error"):
            log(f"Ошибка при запуске экспортера: {result.get('error')}", "ERROR")
            return None
        
        log("Экспортер запущен успешно", "SUCCESS")
        if result.get("exporter"):
            log(f"  Container ID: {result['exporter'].get('container_id', 'N/A')}", "INFO")
        if result.get("network"):
            log(f"  Network: {result['network']}", "INFO")
        if result.get("stack"):
            log(f"  Stack: {result['stack']}", "INFO")
        
        return result
    except requests.exceptions.RequestException as e:
        log(f"Ошибка при запуске экспортера: {e}", "ERROR")
        if hasattr(e, 'response') and e.response is not None:
            log(f"Детали: {e.response.text}", "ERROR")
        return None


def update_containers() -> bool:
    """Обновляет список контейнеров"""
    try:
        log("Обновление списка контейнеров...", "INFO")
        response = requests.patch(f"{CONTAINERS_API}/update_containers")
        response.raise_for_status()
        log("Список контейнеров обновлен", "SUCCESS")
        return True
    except requests.exceptions.RequestException as e:
        log(f"Ошибка при обновлении контейнеров: {e}", "WARNING")
        return False


def get_exporter_port_from_config(config_data: Dict[str, Any]) -> Optional[int]:
    """Извлекает порт экспортера из конфигурации"""
    try:
        config = config_data.get("config", {})
        info = config.get("info", {})
        exporter_port = info.get("exporter_port")
        if exporter_port:
            return int(exporter_port)
    except (ValueError, TypeError):
        pass
    return None


def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        log("Использование: python3 test_container_monitoring.py <container_id> [port]", "ERROR")
        log("Пример: python3 test_container_monitoring.py abc123def456", "INFO")
        sys.exit(1)
    
    container_id = sys.argv[1]
    exporter_port = None
    
    # Опциональный порт из аргументов
    if len(sys.argv) >= 3:
        try:
            exporter_port = int(sys.argv[2])
        except ValueError:
            log(f"Неверный формат порта: {sys.argv[2]}. Используется порт по умолчанию.", "WARNING")
    
    log("=" * 70)
    log("Тест полного цикла подключения мониторинга контейнера", "INFO")
    log("=" * 70)
    log(f"Container ID: {container_id}", "INFO")
    
    # Шаг 1: Получаем информацию о контейнере
    log("\n[Шаг 1] Получение информации о контейнере...", "INFO")
    container_data = get_container(container_id)
    
    if not container_data:
        log(f"Контейнер {container_id} не найден", "ERROR")
        sys.exit(1)
    
    container_name = container_data.get("info", {}).get("Name", "").lstrip("/") or container_id[:12]
    host_id = container_data.get("host_id") or container_data.get("host_name")
    has_config = container_data.get("has_prometheus_config", False)
    
    log(f"  Имя контейнера: {container_name}", "SUCCESS")
    log(f"  Host ID: {host_id}", "SUCCESS")
    log(f"  Статус: {container_data.get('info', {}).get('State', {}).get('Status', 'unknown')}", "SUCCESS")
    log(f"  Конфигурация Prometheus: {'Да' if has_config else 'Нет'}", "SUCCESS")
    
    if not host_id:
        log("Host ID не найден. Невозможно продолжить.", "ERROR")
        sys.exit(1)
    
    config_data = None
    
    # Шаг 2: Генерируем конфигурацию (если еще не создана)
    if not has_config:
        log("\n[Шаг 2] Генерация конфигурации Prometheus...", "INFO")
        config_data = generate_config(container_id, host_id)
        
        if not config_data:
            log("Не удалось сгенерировать конфигурацию", "ERROR")
            sys.exit(1)
        
        # Извлекаем порт экспортера из конфигурации, если не указан
        if exporter_port is None:
            exporter_port = get_exporter_port_from_config(config_data)
            if exporter_port:
                log(f"Используется порт экспортера из конфигурации: {exporter_port}", "INFO")
            else:
                # Порт по умолчанию для большинства экспортеров
                exporter_port = 9100
                log(f"Используется порт по умолчанию: {exporter_port}", "WARNING")
    else:
        log("\n[Шаг 2] Конфигурация уже существует, пропускаем генерацию", "INFO")
        # Пытаемся получить порт из существующей конфигурации
        if exporter_port is None:
            exporter_port = 9100
            log(f"Используется порт по умолчанию: {exporter_port}", "WARNING")
    
    # Шаг 3: Запускаем экспортер
    log(f"\n[Шаг 3] Запуск экспортера на порту {exporter_port}...", "INFO")
    exporter_result = start_exporter(container_id, exporter_port)
    
    if not exporter_result:
        log("Не удалось запустить экспортер", "ERROR")
        sys.exit(1)
    
    # Шаг 4: Обновляем список контейнеров (как на фронтенде)
    log("\n[Шаг 4] Обновление списка контейнеров...", "INFO")
    update_containers()
    
    # Небольшая задержка для обновления данных
    time.sleep(1)
    
    # Шаг 5: Проверяем результат
    log("\n[Шаг 5] Проверка результата...", "INFO")
    updated_container = get_container(container_id)
    
    if updated_container:
        updated_has_config = updated_container.get("has_prometheus_config", False)
        log(f"  Конфигурация Prometheus: {'Да' if updated_has_config else 'Нет'}", 
            "SUCCESS" if updated_has_config else "WARNING")
        
        # Проверяем наличие экспортера
        container_name_normalized = container_name
        exporter_name = f"{container_name_normalized}-exporter"
        
        # Получаем все контейнеры для поиска экспортера
        try:
            response = requests.get(f"{CONTAINERS_API}/containers")
            response.raise_for_status()
            all_containers = response.json()
            
            exporter_found = False
            for cid, cdata in all_containers.items():
                cname = cdata.get("info", {}).get("Name", "").lstrip("/")
                if cname.lower() == exporter_name.lower():
                    exporter_status = cdata.get("info", {}).get("State", {}).get("Status", "unknown")
                    log(f"  Экспортер найден: {exporter_name}", "SUCCESS")
                    log(f"  Статус экспортера: {exporter_status}", 
                        "SUCCESS" if exporter_status == "running" else "WARNING")
                    exporter_found = True
                    break
            
            if not exporter_found:
                log(f"  Экспортер {exporter_name} не найден", "WARNING")
        except Exception as e:
            log(f"  Ошибка при проверке экспортера: {e}", "WARNING")
    
    # Итоги
    log("\n" + "=" * 70)
    log("Тест завершен!", "SUCCESS")
    log("=" * 70)
    log("\nРезультаты:", "INFO")
    log(f"  ✓ Конфигурация Prometheus: {'Создана' if config_data else 'Уже существовала'}", "SUCCESS")
    log(f"  ✓ Экспортер: {'Запущен' if exporter_result else 'Не запущен'}", 
        "SUCCESS" if exporter_result else "ERROR")
    log(f"  ✓ Порт экспортера: {exporter_port}", "INFO")
    
    if exporter_result:
        log("\nДля проверки конфигурации Prometheus:", "INFO")
        log(f"  GET {PROMETHEUS_API}/get_all_configs", "INFO")
        log(f"  GET {PROMETHEUS_API}/get_config_files/<config_id>", "INFO")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\nПрервано пользователем", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"Критическая ошибка: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)

