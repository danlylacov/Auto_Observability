#!/usr/bin/env python3
"""
Скрипт для проверки доступности Docker образов из signatures.yml
Проверяет каждый образ и очищает тестовые контейнеры после проверки.
"""

import yaml
import subprocess
import sys
import time
from typing import Dict, List, Tuple, Optional

SIGNATURES_PATH = "../prometheus_generation/app/services/signatures.yml"


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


def load_signatures() -> Dict:
    """Загружает signatures.yml"""
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
    """Пытается найти альтернативную версию образа"""
    # Если образ с тегом latest, пробуем без тега или с конкретными версиями
    if ":latest" in image_name:
        base_image = image_name.replace(":latest", "")
        
        # Пробуем различные варианты
        alternatives = [
            base_image,  # Без тега
            f"{base_image}:stable",
            f"{base_image}:v1",
            f"{base_image}:1.0",
            f"{base_image}:1",
        ]
        
        for alt in alternatives:
            try:
                # Сначала проверяем через manifest (быстрее, не скачивает)
                manifest_result = subprocess.run(
                    ["docker", "manifest", "inspect", alt],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if manifest_result.returncode == 0:
                    return alt
            except:
                # Если manifest не работает, пробуем pull
                try:
                    pull_result = subprocess.run(
                        ["docker", "pull", alt],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if pull_result.returncode == 0:
                        return alt
                except:
                    continue
    
    return None


def check_image_availability(image_name: str) -> Tuple[bool, str, Optional[str]]:
    """Проверяет доступность Docker образа, возвращает (доступен, сообщение, альтернатива)"""
    try:
        # Пытаемся получить информацию об образе (не скачивая его)
        result = subprocess.run(
            ["docker", "manifest", "inspect", image_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return True, "Доступен", None
        else:
            # Пробуем скачать образ для проверки
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
                # Пытаемся найти альтернативу
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
    """Удаляет тестовый контейнер если он существует"""
    try:
        # Проверяем существование контейнера
        check_result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if container_name in check_result.stdout:
            # Останавливаем и удаляем контейнер
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
    """Тестирует образ, запуская временный контейнер"""
    test_container_name = f"test-{stack_name}-check"
    
    # Очищаем старый контейнер если есть
    cleanup_test_container(test_container_name)
    
    try:
        log(f"  Запуск тестового контейнера...", "INFO")
        
        # Формируем команду docker run
        cmd = ["docker", "run", "-d", "--name", test_container_name]
        
        # Добавляем порт если указан
        if port:
            cmd.extend(["-p", f"{port}:{port}"])
        
        # Добавляем образ
        cmd.append(image_name)
        
        # Запускаем контейнер
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Ждем немного для запуска
            time.sleep(2)
            
            # Проверяем статус
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
        # Всегда очищаем контейнер после проверки
        cleanup_test_container(test_container_name)


def main():
    """Основная функция"""
    log("=" * 80)
    log("Проверка доступности Docker образов из signatures.yml", "INFO")
    log("=" * 80)
    
    # Загружаем signatures
    signatures = load_signatures()
    
    if not signatures:
        log("Signatures пуст или не загружен", "ERROR")
        sys.exit(1)
    
    # Собираем все образы
    images_to_check = []
    
    for stack_name, config in signatures.items():
        if isinstance(config, dict) and "exporter_image" in config:
            image_name = config["exporter_image"]
            exporter_port = config.get("exporter_port", None)
            images_to_check.append((stack_name, image_name, exporter_port))
    
    log(f"\nНайдено образов для проверки: {len(images_to_check)}", "INFO")
    
    # Результаты проверки
    results = {
        "available": [],
        "unavailable": [],
        "tested": [],
        "fixed": []
    }
    
    # Загружаем signatures для обновления
    signatures_to_update = load_signatures()
    signatures_updated = False
    
    # Проверяем каждый образ
    for idx, (stack_name, image_name, port) in enumerate(images_to_check, 1):
        log(f"\n[{idx}/{len(images_to_check)}] Проверка: {stack_name}", "INFO")
        log(f"  Образ: {image_name}", "INFO")
        
        # Проверяем доступность образа
        is_available, status_msg, alternative = check_image_availability(image_name)
        
        if is_available:
            log(f"  Статус: {status_msg}", "SUCCESS")
            results["available"].append((stack_name, image_name))
            
            # Тестируем запуск контейнера
            log(f"  Тестирование запуска контейнера...", "INFO")
            if test_image_with_container(stack_name, image_name, port):
                results["tested"].append((stack_name, image_name))
            else:
                log(f"  Предупреждение: образ доступен, но контейнер не запустился", "WARNING")
        else:
            log(f"  Статус: {status_msg}", "ERROR")
            results["unavailable"].append((stack_name, image_name, status_msg))
            
            # Если найдена альтернатива, обновляем signatures.yml
            if alternative and stack_name in signatures_to_update:
                log(f"  Обновление signatures.yml: {image_name} -> {alternative}", "SUCCESS")
                signatures_to_update[stack_name]["exporter_image"] = alternative
                signatures_updated = True
                results["fixed"].append((stack_name, image_name, alternative))
        
        # Небольшая задержка между проверками
        time.sleep(1)
    
    # Сохраняем обновленный signatures.yml если были изменения
    if signatures_updated:
        log("\n" + "=" * 80)
        log("Сохранение обновлений в signatures.yml", "INFO")
        log("=" * 80)
        
        try:
            with open(SIGNATURES_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(signatures_to_update, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            log(f"Файл {SIGNATURES_PATH} обновлен", "SUCCESS")
            log(f"Исправлено образов: {len(results['fixed'])}", "SUCCESS")
        except Exception as e:
            log(f"Ошибка при сохранении файла: {e}", "ERROR")
    
    # Итоговая статистика
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
    
    # Финальная очистка всех тестовых контейнеров
    log("\n" + "=" * 80)
    log("Финальная очистка тестовых контейнеров", "INFO")
    log("=" * 80)
    
    for stack_name, _, _ in images_to_check:
        test_container_name = f"test-{stack_name}-check"
        cleanup_test_container(test_container_name)
    
    # Проверяем, не осталось ли тестовых контейнеров
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

