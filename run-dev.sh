

cd "$(dirname "$0")"

PID_FILE=".dev-pids"
LOG_DIR=".dev-logs"

if [ "$1" = "start" ]; then
    echo "Starting services..."
    
    if [ -f "$PID_FILE" ]; then
        while read -r pid; do
            kill "$pid" 2>/dev/null || true
        done < "$PID_FILE"
        > "$PID_FILE"
    fi
    
    mkdir -p "$LOG_DIR"
    > "$PID_FILE"
    
    if [ -f "api_agregator/.env.dev" ]; then
        set -a
        source api_agregator/.env.dev
        set +a
    fi
    
    (cd api_agregator && env $(grep -v '^#' .env.dev | xargs) python3 -m app.db.postgres.init_db 2>/dev/null || true)
    
    (cd docker_classification && if [ -f .env.dev ]; then env $(grep -v '^#' .env.dev | xargs) uvicorn app.main:app --host 0.0.0.0 --port 8001 >> "../$LOG_DIR/docker_classification.log" 2>&1; else uvicorn app.main:app --host 0.0.0.0 --port 8001 >> "../$LOG_DIR/docker_classification.log" 2>&1; fi &)
    echo $! >> "$PID_FILE"
    
    (cd prometheus_generation && if [ -f .env.dev ]; then env $(grep -v '^#' .env.dev | xargs) uvicorn app.main:app --host 0.0.0.0 --port 8002 >> "../$LOG_DIR/prometheus_generation.log" 2>&1; else uvicorn app.main:app --host 0.0.0.0 --port 8002 >> "../$LOG_DIR/prometheus_generation.log" 2>&1; fi &)
    echo $! >> "$PID_FILE"
    
    (cd prometheus_manager && if [ -f .env.dev ]; then env $(grep -v '^#' .env.dev | xargs) uvicorn app.main:app --host 0.0.0.0 --port 8003 >> "../$LOG_DIR/prometheus_manager.log" 2>&1; else uvicorn app.main:app --host 0.0.0.0 --port 8003 >> "../$LOG_DIR/prometheus_manager.log" 2>&1; fi &)
    echo $! >> "$PID_FILE"
    
    (cd api_agregator && uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload >> "../$LOG_DIR/api_agregator.log" 2>&1 &)
    echo $! >> "$PID_FILE"
    
    (cd api_agregator && celery -A app.celery_app worker --loglevel=info >> "../$LOG_DIR/celery_worker.log" 2>&1 &)
    echo $! >> "$PID_FILE"
    
    (cd api_agregator && celery -A app.celery_app beat --loglevel=info >> "../$LOG_DIR/celery_beat.log" 2>&1 &)
    echo $! >> "$PID_FILE"
    
    (cd frontend && npm run dev >> "../$LOG_DIR/frontend.log" 2>&1 &)
    echo $! >> "$PID_FILE"
    
    echo "Services started. Logs in $LOG_DIR/"
    echo "Frontend: http://localhost:3000"
    echo "Stop with: $0 stop"

elif [ "$1" = "stop" ]; then
    echo "Stopping services..."
    
    if [ ! -f "$PID_FILE" ]; then
        echo "No services running"
        exit 0
    fi
    
    while read -r pid; do
        kill "$pid" 2>/dev/null || true
    done < "$PID_FILE"
    
    sleep 1
    
    while read -r pid; do
        kill -9 "$pid" 2>/dev/null || true
    done < "$PID_FILE"
    
    > "$PID_FILE"
    echo "Services stopped"

else
    echo "Usage: $0 {start|stop}"
    exit 1
fi
