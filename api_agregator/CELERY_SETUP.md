## Запуск Worker и Beat одновременно

Для запуска обоих компонентов в отдельных терминалах:

**Терминал 1 (Worker):**
```bash
python3 -m celery -A app.celery_app worker --loglevel=info
```

**Терминал 2 (Beat):**
```bash
python3 -m celery -A app.celery_app beat --loglevel=info
```
