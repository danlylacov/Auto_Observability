#!/bin/bash
# Скрипт для запуска docker_api с правильными параметрами
# Запускает сервис на всех интерфейсах (0.0.0.0) для доступа из Docker контейнеров

cd "$(dirname "$0")"

# Проверяем наличие виртуального окружения
if [ -d "../.venv" ]; then
    source ../.venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Запускаем uvicorn на всех интерфейсах
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

