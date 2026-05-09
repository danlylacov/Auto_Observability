#!/bin/bash

# Скрипт для запуска всех микросервисов

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PID_FILE=".services-pids"
LOG_DIR=".services-logs"

# Функция для проверки доступности порта
check_port() {
    local port=$1
    local host=${2:-localhost}
    timeout 1 bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null
}

# Функция для ожидания готовности сервиса
wait_for_service() {
    local name=$1
    local port=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Ожидание готовности $name..."
    while [ $attempt -lt $max_attempts ]; do
        if check_port $port; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    echo -e " ${RED}✗${NC}"
    return 1
}

# Функция запуска сервиса
start_service() {
    local name=$1
    local dir=$2
    local port=$3
    local cmd=$4
    
    if [ ! -d "$dir" ]; then
        echo -e "${YELLOW}Пропуск $name: директория не найдена${NC}"
        return
    fi
    
    echo -e "${BLUE}Запуск $name...${NC}"
    
    cd "$dir"
    
    # Загрузка переменных окружения, если есть
    if [ -f ".env.dev" ]; then
        set -a
        source .env.dev 2>/dev/null || true
        set +a
    fi
    
    # Запуск сервиса в фоне
    eval "$cmd" >> "../$LOG_DIR/${name}.log" 2>&1 &
    local pid=$!
    echo $pid >> "../$PID_FILE"
    
    cd ..
    
    # Ожидание готовности сервиса
    if [ -n "$port" ]; then
        wait_for_service "$name" "$port" || {
            echo -e "${RED}Сервис $name не запустился за отведенное время${NC}"
        }
    fi
}

# Функция остановки сервисов
stop_services() {
    echo -e "${BLUE}Остановка сервисов...${NC}"
    
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${YELLOW}Файл PID не найден. Сервисы могут быть не запущены.${NC}"
        return
    fi
    
    while read -r pid; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "Остановка процесса $pid..."
            kill "$pid" 2>/dev/null || true
        fi
    done < "$PID_FILE"
    
    sleep 2
    
    # Принудительная остановка, если процесс еще работает
    while read -r pid; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "Принудительная остановка процесса $pid..."
            kill -9 "$pid" 2>/dev/null || true
        fi
    done < "$PID_FILE"
    
    > "$PID_FILE"
    echo -e "${GREEN}Сервисы остановлены${NC}"
}

# Функция проверки статуса сервисов
check_status() {
    echo -e "${BLUE}Статус сервисов:${NC}"
    echo ""
    
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${YELLOW}Сервисы не запущены${NC}"
        return
    fi
    
    local services=(
        "api_agregator:8081"
        "docker_api:8000"
        "docker_classification:8001"
        "prometheus_generation:8002"
        "prometheus_manager:8003"
        "grafana_manager:8004"
    )
    
    for service_info in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service_info"
        if check_port "$port"; then
            echo -e "  ${GREEN}✓${NC} $name (порт $port) - работает"
        else
            echo -e "  ${RED}✗${NC} $name (порт $port) - не работает"
        fi
    done
}

# Основная логика
case "${1:-start}" in
    start)
        echo -e "${BLUE}========================================${NC}"
        echo -e "${BLUE}Запуск микросервисов${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo ""
        
        # Очистка старых процессов
        if [ -f "$PID_FILE" ]; then
            stop_services
        fi
        
        # Создание директорий
        mkdir -p "$LOG_DIR"
        > "$PID_FILE"
        
        # Проверка наличия Docker Compose для инфраструктуры
        if command -v docker-compose &> /dev/null || command -v docker &> /dev/null; then
            echo -e "${BLUE}Запуск инфраструктуры (PostgreSQL, Redis, MinIO)...${NC}"
            docker-compose up -d postgres redis minio 2>/dev/null || {
                echo -e "${YELLOW}Предупреждение: не удалось запустить инфраструктуру через docker-compose${NC}"
            }
            sleep 5
        fi
        
        # Инициализация базы данных
        if [ -d "api_agregator" ] && [ -f "api_agregator/.env.dev" ]; then
            echo -e "${BLUE}Инициализация базы данных...${NC}"
            (cd api_agregator && python3 -m app.db.postgres.init_db 2>/dev/null || true)
        fi
        
        # Запуск сервисов
        start_service "docker_api" "docker_api" "8000" \
            "uvicorn app.main:app --host 0.0.0.0 --port 8000"
        
        start_service "docker_classification" "docker_classification" "8001" \
            "uvicorn app.main:app --host 0.0.0.0 --port 8001"
        
        start_service "prometheus_generation" "prometheus_generation" "8002" \
            "uvicorn app.main:app --host 0.0.0.0 --port 8002"
        
        start_service "prometheus_manager" "prometheus_manager" "8003" \
            "uvicorn app.main:app --host 0.0.0.0 --port 8003"
        
        start_service "grafana_manager" "grafana_manager" "8004" \
            "uvicorn app.main:app --host 0.0.0.0 --port 8004"
        
        start_service "api_agregator" "api_agregator" "8081" \
            "uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload"
        
        # Запуск Celery worker и beat
        if [ -d "api_agregator" ]; then
            echo -e "${BLUE}Запуск Celery worker...${NC}"
            (cd api_agregator && celery -A app.celery_app worker --loglevel=info >> "../$LOG_DIR/celery_worker.log" 2>&1 &)
            echo $! >> "$PID_FILE"
            
            echo -e "${BLUE}Запуск Celery beat...${NC}"
            (cd api_agregator && celery -A app.celery_app beat --loglevel=info >> "../$LOG_DIR/celery_beat.log" 2>&1 &)
            echo $! >> "$PID_FILE"
        fi
        
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}Сервисы запущены${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo -e "Логи находятся в директории: ${BLUE}$LOG_DIR${NC}"
        echo ""
        echo -e "Доступные сервисы:"
        echo -e "  - API Aggregator: ${BLUE}http://localhost:8081${NC}"
        echo -e "  - Docker API: ${BLUE}http://localhost:8000${NC}"
        echo -e "  - Docker Classification: ${BLUE}http://localhost:8001${NC}"
        echo -e "  - Prometheus Generation: ${BLUE}http://localhost:8002${NC}"
        echo -e "  - Prometheus Manager: ${BLUE}http://localhost:8003${NC}"
        echo -e "  - Grafana Manager: ${BLUE}http://localhost:8004${NC}"
        echo ""
        echo -e "Для остановки используйте: ${YELLOW}$0 stop${NC}"
        ;;
    
    stop)
        stop_services
        ;;
    
    status)
        check_status
        ;;
    
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    
    *)
        echo "Использование: $0 {start|stop|status|restart}"
        echo ""
        echo "Команды:"
        echo "  start   - Запустить все сервисы"
        echo "  stop    - Остановить все сервисы"
        echo "  status  - Показать статус сервисов"
        echo "  restart - Перезапустить все сервисы"
        exit 1
        ;;
esac

