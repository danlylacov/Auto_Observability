#!/usr/bin/env python3
"""
Скрипт для проверки доступности Docker образов из signatures.yml.

Проверяет каждый образ и очищает тестовые контейнеры после проверки.
"""

import sys
import time
import logging
from typing import Dict, List, Tuple, Optional

import yaml
import subprocess

SIGNATURES_PATH = "../prometheus_generation/app/services/signatures.yml"

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def log(message: str, level: str = "INFO"):
    """
    Логирование с цветами для консольного вывода.

    Args:
        message: Сообщение для логирования
        level: Уровень логирования (INFO, SUCCESS, ERROR, WARNING)
    """
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "ERROR": "\033[91m",
        "WARNING": "\033[93m",
        "RESET": "\033[0m"
    }
    logger.info(f"{colors.get(level, '')}[{level}]{colors['RESET']} {message}")


def load_signatures() -> Dict:
    """
    Загружает signatures.yml.

    Returns:
        Dict: Содержимое файла signatures.yml

    Raises:
        SystemExit: При ошибке загрузки файла
    """
    try:
        with open(SIGNATURES_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        log(f"Файл {SIGNATURES_PATH} не найден", "ERROR")
        sys.exit(1)
    except yaml.YAMLError as e:
        log(f"Ошибка при парсинге YAML: {e}", "ERROR")
        sys.exit(1)


def find_alternative_image(image_name: str) -> Optional[str]:
    """
    Пытается найти альтернативную версию образа.

    Args:
        image_name: Имя образа для поиска альтернативы

    Returns:
        Optional[str]: Альтернативное имя образа или None
    """
    if ":latest" in image_name:
        base_image = image_name.replace(":latest", "")

        alternatives = [
            base_image,
            f"{base_image}:stable",
            f"{base_image}:v1",
            f"{base_image}:1.0",
            f"{base_image}:1",
        ]

        for alt in alternatives:
            try:
                manifest_result = subprocess.run(
                    ["docker", "manifest", "inspect", alt],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if manifest_result.returncode == 0:
                    return alt
            except Exception:
                try:
                    pull_result = subprocess.run(
                        ["docker", "pull", alt],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if pull_result.returncode == 0:
                        return alt
                except Exception:
                    continue

    return None


def check_image_availability(image_name: str) -> Tuple[bool, str, Optional[str]]:
    """
    Проверяет доступность Docker образа.

    Args:
        image_name: Имя образа для проверки

    Returns:
        Tuple[bool, str, Optional[str]]: (доступен, сообщение, альтернатива)
    """
    try:
        result = subprocess.run(
            ["docker", "manifest", "inspect", image_name],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return True, "Доступен", None
        else:
            log(f"  Попытка скачать образ для проверки...", "INFO")
            pull_result = subprocess.run(
                ["docker", "pull", image_name],
                capture_output=True,
                text=True,
                timeout=60
            )

            if pull_result.returncode == 0:
                return True, "Доступен (скачан)", None
            else:
                log(f"  Поиск альтернативного образа...", "INFO")
                alternative = find_alternative_image(image_name)
                if alternative:
                    log(f"  Найдена альтернатива: {alternative}", "SUCCESS")
                    return False, f"Недоступен, найдена альтернатива: {alternative}", alternative
                else:
                    error_msg = pull_result.stderr.strip()[:100]
                    return False, f"Недоступен: {error_msg}", None
    except subprocess.TimeoutExpired:
        return False, "Таймаут при проверке", None
    except FileNotFoundError:
        return False, "Docker не установлен", None
    except Exception as e:
        return False, f"Ошибка: {str(e)[:100]}", None


def cleanup_test_container(container_name: str):
    """
    Удаляет тестовый контейнер если он существует.

    Args:
        container_name: Имя контейнера для удаления
    """
    try:
        check_result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if container_name in check_result.stdout:
            subprocess.run(
                ["docker", "stop", container_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            log(f"  Контейнер {container_name} удален", "SUCCESS")
    except Exception as e:
        log(f"  Ошибка при удалении контейнера {container_name}: {e}", "WARNING")


def test_image_with_container(stack_name: str, image_name: str, port: int = None) -> bool:
    """
    Тестирует образ, запуская временный контейнер.

    Args:
        stack_name: Имя стека
        image_name: Имя образа
        port: Порт для проброса (опционально)

    Returns:
        bool: True если контейнер запустился успешно
    """
    test_container_name = f"test-{stack_name}-check"

    cleanup_test_container(test_container_name)

    try:
        log(f"  Запуск тестового контейнера...", "INFO")

        cmd = ["docker", "run", "-d", "--name", test_container_name]

        if port:
            cmd.extend(["-p", f"{port}:{port}"])

        cmd.append(image_name)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            time.sleep(2)

            status_result = subprocess.run(
                ["docker", "ps", "--filter", f"name={test_container_name}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True
            )

            if test_container_name in status_result.stdout or "Up" in status_result.stdout:
                log(f"  Контейнер запущен успешно", "SUCCESS")
                return True
            else:
                log(f"  Контейнер не запустился", "WARNING")
                return False
        else:
            error_msg = result.stderr.strip()[:150]
            log(f"  Ошибка запуска: {error_msg}", "ERROR")
            return False

    except subprocess.TimeoutExpired:
        log(f"  Таймаут при запуске контейнера", "ERROR")
        return False
    except Exception as e:
        log(f"  Ошибка: {str(e)[:100]}", "ERROR")
        return False
    finally:
        cleanup_test_container(test_container_name)


def main():
    """
    Основная функция проверки доступности Docker образов.

    Загружает signatures.yml, проверяет доступность всех образов,
    тестирует их запуск и обновляет файл при необходимости.
    """
    log("=" * 80)
    log("Проверка доступности Docker образов из signatures.yml", "INFO")
    log("=" * 80)

    signatures = load_signatures()

    if not signatures:
        log("Signatures пуст или не загружен", "ERROR")
        sys.exit(1)

    images_to_check = []

    for stack_name, config in signatures.items():
        if isinstance(config, dict) and "exporter_image" in config:
            image_name = config["exporter_image"]
            exporter_port = config.get("exporter_port", None)
            images_to_check.append((stack_name, image_name, exporter_port))

    log(f"\nНайдено образов для проверки: {len(images_to_check)}", "INFO")

    results = {
        "available": [],
        "unavailable": [],
        "tested": [],
        "fixed": []
    }

    signatures_to_update = load_signatures()
    signatures_updated = False

    for idx, (stack_name, image_name, port) in enumerate(images_to_check, 1):
        log(f"\n[{idx}/{len(images_to_check)}] Проверка: {stack_name}", "INFO")
        log(f"  Образ: {image_name}", "INFO")

        is_available, status_msg, alternative = check_image_availability(image_name)

        if is_available:
            log(f"  Статус: {status_msg}", "SUCCESS")
            results["available"].append((stack_name, image_name))

            log(f"  Тестирование запуска контейнера...", "INFO")
            if test_image_with_container(stack_name, image_name, port):
                results["tested"].append((stack_name, image_name))
            else:
                log(f"  Предупреждение: образ доступен, но контейнер не запустился", "WARNING")
        else:
            log(f"  Статус: {status_msg}", "ERROR")
            results["unavailable"].append((stack_name, image_name, status_msg))

            if alternative and stack_name in signatures_to_update:
                log(f"  Обновление signatures.yml: {image_name} -> {alternative}", "SUCCESS")
                signatures_to_update[stack_name]["exporter_image"] = alternative
                signatures_updated = True
                results["fixed"].append((stack_name, image_name, alternative))

        time.sleep(1)

    if signatures_updated:
        log("\n" + "=" * 80)
        log("Сохранение обновлений в signatures.yml", "INFO")
        log("=" * 80)

        try:
            with open(SIGNATURES_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(
                    signatures_to_update,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )
            log(f"Файл {SIGNATURES_PATH} обновлен", "SUCCESS")
            log(f"Исправлено образов: {len(results['fixed'])}", "SUCCESS")
        except Exception as e:
            log(f"Ошибка при сохранении файла: {e}", "ERROR")

    log("\n" + "=" * 80)
    log("ИТОГОВАЯ СТАТИСТИКА", "INFO")
    log("=" * 80)

    log(f"\n✓ Доступные образы: {len(results['available'])}", "SUCCESS")
    for stack_name, image_name in results["available"]:
        log(f"  - {stack_name}: {image_name}", "SUCCESS")

    log(f"\n✓ Успешно протестированные контейнеры: {len(results['tested'])}", "SUCCESS")
    for stack_name, image_name in results["tested"]:
        log(f"  - {stack_name}: {image_name}", "SUCCESS")

    log(f"\n✗ Недоступные образы: {len(results['unavailable'])}", "ERROR")
    for stack_name, image_name, error in results["unavailable"]:
        log(f"  - {stack_name}: {image_name}", "ERROR")
        log(f"    Причина: {error}", "ERROR")

    if results["fixed"]:
        log(f"\n✓ Исправленные образы: {len(results['fixed'])}", "SUCCESS")
        for stack_name, old_image, new_image in results["fixed"]:
            log(f"  - {stack_name}: {old_image} -> {new_image}", "SUCCESS")

    log("\n" + "=" * 80)
    log("Финальная очистка тестовых контейнеров", "INFO")
    log("=" * 80)

    for stack_name, _, _ in images_to_check:
        test_container_name = f"test-{stack_name}-check"
        cleanup_test_container(test_container_name)

    cleanup_result = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=test-", "--format", "{{.Names}}"],
        capture_output=True,
        text=True
    )

    remaining = [name for name in cleanup_result.stdout.strip().split('\n') if name]
    if remaining:
        log(f"\nОставшиеся тестовые контейнеры: {len(remaining)}", "WARNING")
        for name in remaining:
            log(f"  - {name}", "WARNING")
            cleanup_test_container(name)
    else:
        log("\nВсе тестовые контейнеры очищены", "SUCCESS")

    log("\n" + "=" * 80)
    log("Проверка завершена!", "SUCCESS")
    log("=" * 80)


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

