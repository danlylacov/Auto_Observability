# Auto Observability


![Pylint](.badges/pylint.svg)

Система автоматического мониторинга Docker-контейнеров: классификация стека, генерация конфигураций Prometheus, импорт дашбордов Grafana, управление контейнерами Prometheus/Grafana на хосте и **JWT-аутентификация** веб-интерфейса (отдельный сервис пользователей).

## Технологический стек

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Vue.js](https://img.shields.io/badge/Vue.js-3.4-4FC08D?style=flat-square&logo=vue.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?style=flat-square&logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=flat-square&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?style=flat-square&logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.3-37814A?style=flat-square&logo=celery&logoColor=white)
![MinIO](https://img.shields.io/badge/MinIO-S3-FFC649?style=flat-square&logo=minio&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-24.0-2496ED?style=flat-square&logo=docker&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-2.45-E6522C?style=flat-square&logo=prometheus&logoColor=white)

## Описание

Auto Observability — это платформа для автоматического обнаружения, классификации и мониторинга Docker-контейнеров в распределённой инфраструктуре. Система определяет стек контейнера, генерирует конфигурации Prometheus, при необходимости подтягивает дашборды с grafana.com и проксирует операции запуска/остановки Prometheus и Grafana через отдельные менеджеры. Доступ к API агрегатора защищён JWT (токены выдаёт **Users API** с тем же секретом, что и проверка на стороне агрегатора).

### Основные возможности

- Автоматическое обнаружение контейнеров на множестве хостов
- Интеллектуальная классификация технологического стека контейнеров
- Автоматическая генерация конфигураций Prometheus
- Управление экспортерами метрик и жизненным циклом контейнеров Prometheus/Grafana на хосте (через менеджеры)
- Импорт и настройка дашбордов Grafana по шаблонам из `signatures.yml` (в т.ч. с grafana.com)
- Централизованное хранение конфигураций в MinIO
- Вход в веб-интерфейс по логину/паролю (JWT), роли пользователей в PostgreSQL
- Веб-интерфейс для управления и мониторинга
- Фоновые задачи (Celery) для автоматического обновления данных


### Поток данных

1. **Аутентификация**: пользователь получает JWT через **Users API**; **API Aggregator** принимает запросы только с валидным токеном.
2. **Обнаружение контейнеров**: API Aggregator запрашивает контейнеры через **Docker API** на каждом хосте.
3. **Классификация**: контейнер отправляется в **Docker Classification** для определения стека.
4. **Хранение**: данные кешируются в Redis, метаданные — в PostgreSQL.
5. **Генерация Prometheus**: **Prometheus Generation** строит `scrape_config` / targets и env для экспортёра, сохраняет артефакты в MinIO.
6. **Применение конфигурации**: при необходимости **Prometheus Manager** подтягивает конфиг из MinIO и обновляет Prometheus на хосте.
7. **Grafana**: **Grafana Generation** загружает шаблон дашборда (по `grafana_dashboard_id` из `signatures.yml` или по ID) и импортирует его в вашу Grafana; **Grafana Manager** управляет Docker-контейнером Grafana на хосте.
8. **Запуск экспортера**: соответствующий экспортёр поднимается в сети целевого контейнера.

## Сводка портов (Docker Compose)

| Сервис | Порт на хосте | Примечание |
|--------|----------------|------------|
| Frontend | 3000 | Nginx: `/api/v1/auth`, `/api/v1/users` → users_api, остальное → api_agregator |
| API Aggregator | 8081 | |
| Users API | 8082 | переопределение: `USERS_API_HOST_PORT` |
| Docker Classification | 8001 | |
| Prometheus Generation | 8002 | |
| Prometheus Manager | 8003 | |
| Docker API | 8004 | смонтирован `docker.sock` |
| Grafana Manager | 8005 | |
| Grafana Generation | 18010 | по умолчанию; переменная `GRAFANA_GENERATION_HOST_PORT` |
| MinIO API / Console | 9002 / 9003 | |

Внутри Docker-сети все приложения слушают **8000** в контейнере, кроме случаев, указанных в `docker-compose.yml`.

## Сервисы

### API Aggregator

**Порт**: 8081  
**Технологии**: FastAPI, PostgreSQL, Redis, Celery

Центральный сервис-агрегатор, предоставляющий единый API для операций системы. Запросы к бизнес-роутерам требуют заголовок `Authorization: Bearer <JWT>` (токен выдаёт **Users API**; секрет `JWT_SECRET` должен совпадать у обоих сервисов и в `docker-compose.yml`).

**Основные функции**:
- Управление хостами (добавление, обновление, удаление)
- Управление контейнерами (получение списка, запуск, остановка, удаление)
- Генерация конфигураций Prometheus и проксирование к **Prometheus Manager**
- Запуск экспортеров метрик
- Управление подписями (signatures) для классификации
- Получение всех активных конфигураций
- Операции Grafana: проксирование к **Grafana Generation** (импорт дашбордов, правка `signatures.yml` через сервис) и к **Grafana Manager** (старт/стоп контейнера Grafana)

**Роутеры**:
- `/api/v1/containers` — управление контейнерами
- `/api/v1/prometheus` — управление конфигурациями Prometheus
- `/api/v1/hosts` — управление хостами
- `/api/v1/grafana` — дашборды и управление Grafana (агрегирует вызовы к grafana_generation / grafana_manager)

**Фоновые задачи (Celery)**:
- Обновление информации о контейнерах (каждую минуту)
- Обновление информации о хостах (каждые 15 секунд)

**Базы данных**:
- PostgreSQL: метаданные контейнеров, хостов, конфигураций Prometheus, связей с дашбордами Grafana
- Redis: кеш данных о контейнерах и хостах

### Users API

**Порт (Compose на хосте)**: 8082 (переменная `USERS_API_HOST_PORT`)  
**Технологии**: FastAPI, PostgreSQL

Сервис аутентификации и пользователей: выдача JWT, учётные записи в той же БД `auto_observability`. При первом старте создаётся роль **maintainer** и пользователь из переменных `MAINTAINER_USERNAME` / `MAINTAINER_PASSWORD` (см. комментарии в `docker-compose.yml`).

**Роутеры**:
- `/api/v1/auth` — вход, обновление токена
- `/api/v1/users` — управление пользователями (для роли maintainer)

Во **frontend** при `npm run dev` запросы на `/api/v1/auth` и `/api/v1/users` проксируются на `VITE_USERS_API_URL` (по умолчанию `http://localhost:8082`).

### Docker API

**Порт**: при локальном запуске по документации ниже — **8000**; в **Docker Compose** на хост проброшен **8004** (`8004:8000`).  
**Технологии**: FastAPI, Docker SDK

Сервис для взаимодействия с Docker daemon на удаленных хостах.

**Основные функции**:
- Обнаружение всех контейнеров на хосте
- Управление жизненным циклом контейнеров (start, stop, remove)
- Запуск новых контейнеров (pull and run)
- Получение детальной информации о контейнерах

**Роутеры**:
- `/api/v1/discover` — обнаружение контейнеров
- `/api/v1/manage` — управление контейнерами

**Особенности**:
- Работает напрямую с Docker SDK
- Поддерживает подключение к удаленным Docker daemons
- Автоматическое определение сетей контейнеров

### Docker Classification

**Порт (Compose на хосте)**: 8001  
**Технологии**: FastAPI, PyYAML

Сервис для автоматической классификации технологического стека контейнеров.

**Основные функции**:
- Анализ меток (labels) контейнера
- Анализ переменных окружения (env)
- Анализ образа (image)
- Анализ открытых портов
- Взвешенная система оценки для определения стека

**Алгоритм классификации**:
- Использует файл `docker_classification/app/services/signatures.yml` с правилами классификации
- Каждое правило имеет вес (weight)
- Система суммирует веса по всем признакам
- Возвращает отсортированный список технологий с вероятностями

**Роутеры**:
- `/api/v1/classificate` — классификация контейнера

**Поддерживаемые технологии**:
- Базы данных: PostgreSQL, MySQL, MongoDB, Redis, Cassandra и др.
- Message brokers: RabbitMQ, Kafka, NATS, ActiveMQ
- Web-серверы: Nginx, Apache, Caddy
- Application servers: Tomcat, Jetty, WildFly
- И многие другие

### Prometheus Generation

**Порт (Compose на хосте)**: 8002 (в контейнере приложение слушает 8000)  
**Технологии**: FastAPI, MinIO (S3), PyYAML

Сервис для генерации конфигураций Prometheus на основе классификации контейнеров.

**Основные функции**:
- Генерация scrape_config для Prometheus
- Генерация targets файла
- Создание переменных окружения для экспортеров
- Определение Docker-сети для экспортера
- Сохранение конфигураций в MinIO

**Роутеры**:
- `/api/v1/generate` — генерация конфигурации
- `/api/v1/signature` — управление подписями
- `/api/v1/main-config` — работа с главным конфигом Prometheus (через агрегатор)

**Конфигурация экспортеров**:
- Использует файл `signatures.yml` в корне проекта: настройки экспортеров Prometheus и (опционально) идентификаторы дашбордов Grafana (`grafana_dashboard_id`) для каждого стека
- Файл содержит конфигурации портов, образов и переменных окружения для каждого типа стека
- При запуске в Docker файл монтируется в контейнер как `/app/signatures.yml` (тот же bind-монтаж использует сервис `grafana_generation`)

**Формат конфигурации**:
- `scrape_config.yml` — конфигурация для Prometheus
- `targets.yml` — список целей для скрейпинга

**Хранение**:
- Конфигурации сохраняются в MinIO (S3-совместимое хранилище)
- Организация по контейнерам: `prometheus/{container_id}/`

### Prometheus Manager

**Порт (Compose на хосте)**: 8003  
**Технологии**: FastAPI, MinIO, Docker SDK

Управление контейнером Prometheus на хосте: старт/стоп/перезапуск, подтягивание сгенерированных конфигов из MinIO. В Compose задаются путь к конфигу на хосте (`PROMETHEUS_CONFIG_HOST_PATH`) и при необходимости volume с `prometheus.yml` (см. `docker-compose.yml`).

**Роутеры** (префикс `/api/v1/manage`):
- `POST .../prometheus/start`, `.../stop`, `.../restart` — жизненный цикл контейнера Prometheus
- эндпоинты обновления конфигурации — в интерактивной документации `/docs`

### Grafana Manager

**Порт (Compose на хосте)**: 8005  
**Технологии**: FastAPI, Docker SDK

Управление Docker-контейнером Grafana на хосте. Имена контейнера, порты и тома задаются в `grafana_manager/app/services/grafana_settings.yml`.

**Роутеры** (префикс `/api/v1/manage`):
- `POST .../grafana/start`, `.../stop`, `.../restart` — жизненный цикл Grafana

### Grafana Generation

**Порт (Compose на хосте)**: по умолчанию **18010** (переменная `GRAFANA_GENERATION_HOST_PORT`)  
**Технологии**: FastAPI, PyYAML, HTTP-клиент к Grafana API

Скачивание шаблонов дашбордов с **grafana.com**, подстановка datasource Prometheus и импорт в вашу Grafana. Использует тот же `signatures.yml`, что и Prometheus Generation (в Compose монтируется в `/app/signatures.yml`).

Переменные окружения: `GRAFANA_URL`, `GRAFANA_USER`, `GRAFANA_PASSWORD`, `DEFAULT_PROMETHEUS_DS_UID` (см. `docker-compose.yml`; по умолчанию ожидается Grafana на хосте, например `http://host.docker.internal:3052`).

**Роутеры** (префикс `/api/v1/grafana`):
- `GET /templates` — индекс шаблонов из `signatures.yml`
- `GET|PUT /templates_yml` — чтение и запись единого YAML
- `POST /import_dashboard` — импорт по `template_key` или числовому `dashboard_id`
- удаление дашборда — см. `/docs`

### Frontend

**Порт**: **3000** при `npm run dev` (см. `frontend/vite.config.ts`); в Docker Compose — **3000** (nginx). Сборка `npm run build`: preview **4173**  
**Технологии**: Vue.js 3, TypeScript, Vite, CodeMirror

Веб-интерфейс для управления системой мониторинга.

**Основные функции**:
- Вход по логину/паролю (JWT); для роли maintainer — управление пользователями
- Просмотр списка хостов и их статусов
- Просмотр контейнеров с фильтрацией по хостам
- Детальная информация о контейнерах
- Генерация конфигураций Prometheus
- Запуск экспортеров метрик
- Просмотр и редактирование единого `signatures.yml` (Prometheus + Grafana) и настроек Prometheus Manager
- Просмотр всех активных конфигураций
- Просмотр файлов конфигураций из MinIO

**Компоненты**:
- `ContainerList` — список контейнеров
- `ContainerDetails` — детали контейнера
- `ExporterControl` — управление экспортерами
- `PrometheusConfig` — просмотр конфигураций
- `HostsView` — управление хостами

## Установка и запуск

### Требования

- Python 3.11+
- Node.js 18+
- Docker и Docker Compose
- PostgreSQL 15+
- Redis 7+
- MinIO (или S3-совместимое хранилище)

### Структура проекта

```
Auto_Observability/
├── signatures.yml                    # Единый YAML стеков: экспортеры Prometheus + grafana_dashboard_id
├── docker-compose.yml                # Полный стек: БД, Redis, MinIO, все микросервисы, frontend
├── run-dev.sh                        # Частичный локальный запуск (см. комментарий ниже)
├── users_api/                        # JWT и пользователи (PostgreSQL)
├── api_agregator/                    # API Aggregator
├── docker_api/                       # Docker API
├── docker_classification/            # Классификация стека
├── prometheus_generation/            # Генерация конфигов Prometheus
├── prometheus_manager/               # Управление контейнером Prometheus на хосте
├── grafana_manager/                  # Управление контейнером Grafana на хосте
├── grafana_generation/               # Импорт дашбордов Grafana (grafana.com + API)
└── frontend/                         # Vue SPA + прокси на aggregator и users_api
```

Скрипт `run-dev.sh` поднимает только часть сервисов (classification, prometheus_generation, prometheus_manager, api_agregator, celery, frontend) и **не** запускает `users_api`, `docker_api`, `grafana_*` — для полного набора используйте `docker compose up` или допишите локальный запуск вручную.

### Настройка окружения

Создайте файлы `.env.dev` в каждом сервисе для локальной разработки:

**api_agregator/.env.dev** (добавьте переменные, совпадающие с `api_agregator/.env.example`; для Docker Compose см. также корневой `.env` / переменные в `docker-compose.yml`):

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=auto_observability
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
MINIO_ENDPOINT=http://localhost:9002
MINIO_USR=minioadmin
MINIO_PWD=minioadmin
DOCKER_API_URL=http://localhost:8004
DOCKER_CLASSIFICATION_API_URL=http://localhost:8001
PROMETHEUS_GENERATION_URL=http://localhost:8002
PROMETHEUS_MANAGER_URL=http://localhost:8003
GRAFANA_MANAGER_URL=http://localhost:8005
GRAFANA_GENERATION_URL=http://localhost:18010
JWT_SECRET=тот-же-секрет-что-и-в-users_api
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
```

**frontend/.env.dev** (для `npm run dev`; порт dev-сервера Vite — 3000):

```env
VITE_API_URL=http://localhost:8081
VITE_USERS_API_URL=http://localhost:8082
```

Создайте `.env.dev` / `.env` по примерам в `users_api/.env.example`, `grafana_generation` (при локальном запуске), `docker_api`, и т.д. Для первого входа в UI при работе через Compose задайте `JWT_SECRET` в корне рядом с `docker-compose.yml` и учётку maintainer (`MAINTAINER_USERNAME` / `MAINTAINER_PASSWORD`).

Аналогично настройте остальные сервисы (`prometheus_generation`, `prometheus_manager`, `docker_classification`, `docker_api`).

### Установка зависимостей

**Backend сервисы** (из корня репозитория):

```bash
pip install -r api_agregator/requirements.txt
pip install -r users_api/requirements.txt
pip install -r docker_api/requirements.txt
pip install -r docker_classification/requirements.txt
pip install -r prometheus_generation/requirements.txt
pip install -r prometheus_manager/requirements.txt
pip install -r grafana_manager/requirements.txt
pip install -r grafana_generation/requirements.txt
```

**Frontend**:
```bash
cd frontend && npm install
```

### Инициализация базы данных

```bash
cd api_agregator
python -m app.db.postgres.init_db
```

### Запуск сервисов

**Локальная разработка (рекомендуется)**:
```bash
./run-dev.sh start
```

Скрипт `run-dev.sh` (без Docker) выполняет:
- попытку инициализации схемы БД (`init_db`), если доступен PostgreSQL из `api_agregator/.env.dev`
- запуск **docker_classification**, **prometheus_generation**, **prometheus_manager**, **api_agregator** (uvicorn), **Celery** worker и beat, **frontend**

Инфраструктуру (**PostgreSQL**, **Redis**, **MinIO**) и сервисы **users_api**, **docker_api**, **grafana_manager**, **grafana_generation** скрипт **не** поднимает — их нужно запустить отдельно (`docker compose up ...` или вручную), иначе вход в UI и вызовы к Docker/Grafana не заработают.

**Остановка сервисов**:
```bash
./run-dev.sh stop
```

**Запуск через Docker Compose** (полный стек; задайте в корне репозитория файл `.env` с `JWT_SECRET` или экспортируйте переменную — см. комментарий в `docker-compose.yml`):

```bash
docker compose up -d
```

**Ручной запуск отдельных сервисов** (для отладки):

API Aggregator:
```bash
cd api_agregator
source .env.dev 2>/dev/null || true
uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
```

Celery Worker:
```bash
cd api_agregator
source .env.dev 2>/dev/null || true
celery -A app.celery_app worker --loglevel=info
```

Celery Beat:
```bash
cd api_agregator
source .env.dev 2>/dev/null || true
celery -A app.celery_app beat --loglevel=info
```

Docker API:
```bash
cd docker_api
source .env.dev 2>/dev/null || true
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Docker Classification:
```bash
cd docker_classification
source .env.dev 2>/dev/null || true
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Prometheus Generation:
```bash
cd prometheus_generation
source .env.dev 2>/dev/null || true
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

Prometheus Manager:
```bash
cd prometheus_manager
source .env.dev 2>/dev/null || true
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

Users API:
```bash
cd users_api
source .env.dev 2>/dev/null || true
uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload
```

Grafana Manager:
```bash
cd grafana_manager
source .env.dev 2>/dev/null || true
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

Grafana Generation:
```bash
cd grafana_generation
source .env.dev 2>/dev/null || true
uvicorn app.main:app --host 0.0.0.0 --port 18010 --reload
```

Frontend:
```bash
cd frontend
source .env.dev 2>/dev/null || true
npm run dev
```

## Использование

### Вход в веб-интерфейс

1. При работе через **Docker Compose** откройте `http://localhost:3000/login` и войдите под учётной записью **maintainer** (логин/пароль из `MAINTAINER_USERNAME` / `MAINTAINER_PASSWORD`, по умолчанию см. `docker-compose.yml`).
2. При локальной разработке поднимите **users_api** и убедитесь, что `JWT_SECRET` совпадает с **api_agregator**; во frontend задайте `VITE_USERS_API_URL` на URL users_api.

### Добавление хоста

1. Откройте веб-интерфейс
2. Перейдите в раздел "Hosts"
3. Добавьте новый хост с указанием имени, адреса и порта Docker API

### Обнаружение контейнеров

1. Система автоматически обновляет список контейнеров каждую минуту
2. Или вручную через API: `PATCH /api/v1/containers/update_containers`

### Генерация конфигурации Prometheus

1. Выберите контейнер из списка
2. Нажмите "Generate Config"
3. Система автоматически:
   - Классифицирует контейнер
   - Сгенерирует конфигурацию Prometheus
   - Сохранит её в MinIO
   - Создаст запись в базе данных

### Запуск экспортера

1. После генерации конфигурации нажмите "Start Exporter"
2. Укажите порт для экспортера
3. Система автоматически:
   - Запустит соответствующий экспортер
   - Подключит его к сети контейнера
   - Настроит переменные окружения

### Интеграция с Prometheus

1. Получите конфигурационные файлы через API: `GET /api/v1/prometheus/get_config_files/{config_id}`
2. Используйте `scrape_config.yml` в вашем `prometheus.yml`
3. Используйте `targets.yml` для динамического обнаружения целей

## Конфигурация

### Файл signatures.yml

Файл `signatures.yml` находится в корне проекта и описывает для каждого стека параметры экспортера Prometheus и при необходимости идентификатор дашборда на grafana.com (`grafana_dashboard_id`). При запуске через Docker Compose файл монтируется в контейнеры `prometheus_generation` и `grafana_generation` как `/app/signatures.yml`.

**Структура конфигурации**:
```yaml
mongodb:
  job_name_suffix: "_mongodb"
  exporter_port: 9216
  metrics_path: "/metrics"
  exporter_image: "percona/mongodb_exporter:0.39"
  grafana_dashboard_id: 7353
  env_vars:
    MONGODB_URI: "mongodb://localhost:27017"
  env_template: "mongodb://{user}:{password}@{host}:{port}/{database}"
```

**Важно**: При локальной разработке файл должен находиться в корне проекта. При запуске через Docker Compose файл монтируется автоматически.

## API Документация

После запуска сервисов документация Swagger доступна по адресам:

| Сервис | URL (хост при `docker compose`, см. таблицу портов) |
|--------|-----------------------------------------------------|
| API Aggregator | http://localhost:8081/docs |
| Users API | http://localhost:8082/docs |
| Docker API | http://localhost:8004/docs |
| Docker Classification | http://localhost:8001/docs |
| Prometheus Generation | http://localhost:8002/docs |
| Prometheus Manager | http://localhost:8003/docs |
| Grafana Manager | http://localhost:8005/docs |
| Grafana Generation | http://localhost:18010/docs |

## Лицензия

Проект разработан в рамках дипломной работы.

Архитектура:
[клик](https://miro.com/welcomeonboard/b3NGc3RkMnlLTGtMckk4ckg1Ykxva2Q4NUlQemNwUDZ5VXFORlRObENrWHBMYTI3eXFJZjdxZWtaOXdwZm5tcklsSDZNRlFrSXh3cUNhaXhJQWFwWjRNR3RGUDJxd0RuZi9mOFFQVHZEVkk3MCs5WENlK1k3YUNFQTQ0Slo2c09Bd044SHFHaVlWYWk0d3NxeHNmeG9BPT0hdjE=?share_link_id=535618662280)
