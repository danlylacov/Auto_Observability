# Тестирование фронтенда

## Проверка работы

1. **API должен быть запущен:**
   ```bash
   # Проверка здоровья API
   curl http://localhost:8081/health
   ```

2. **Запуск фронтенда:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Откройте браузер:**
   - Перейдите на http://localhost:3000
   - Должен отобразиться список контейнеров

## Тестируемые функции

### 1. Список контейнеров
- ✅ Загрузка списка контейнеров
- ✅ Фильтрация по статусу (All, Running, Stopped)
- ✅ Поиск по имени контейнера
- ✅ Обновление списка (кнопка Refresh)

### 2. Действия с контейнерами
- ✅ Start - запуск контейнера
- ✅ Stop - остановка контейнера
- ✅ Remove - удаление контейнера
- ✅ Details - просмотр деталей

### 3. Детали контейнера
- ✅ Просмотр основной информации
- ✅ Network settings
- ✅ Ports
- ✅ Environment variables
- ✅ Labels

### 4. Prometheus
- ✅ Генерация конфигурации
- ✅ Запуск экспортера с указанием порта

## Известные проблемы

1. **Ошибка "Failed to refresh containers"** - исправлено:
   - Убрана неопределенная переменная `host` из `get_containers()`
   - Улучшена обработка ошибок во фронтенде

2. **CORS** - настроен для работы с фронтендом

## Проверка API endpoints

```bash
# Получить все контейнеры
curl http://localhost:8081/api/v1/containers/containers

# Обновить контейнеры
curl -X PATCH http://localhost:8081/api/v1/containers/update_containers

# Запустить контейнер
curl -X POST "http://localhost:8081/api/v1/containers/container/start?id=CONTAINER_ID"

# Остановить контейнер
curl -X POST "http://localhost:8081/api/v1/containers/container/stop?id=CONTAINER_ID"

# Удалить контейнер
curl -X DELETE "http://localhost:8081/api/v1/containers/container/remove?id=CONTAINER_ID"

# Генерация конфига Prometheus
curl -X POST "http://localhost:8081/api/v1/prometheus/generate_config?container_id=CONTAINER_ID"

# Запуск экспортера
curl -X POST "http://localhost:8081/api/v1/prometheus/up_exporter?container_id=CONTAINER_ID&port=9187"
```

