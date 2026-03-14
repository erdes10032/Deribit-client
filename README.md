# Deribit Client

Сервис для периодического получения цен криптовалют с биржи Deribit и предоставления API для доступа к сохранённым данным.

Приложение каждые 60 секунд получает **index price** для:

- BTC/USD
- ETH/USD

После чего сохраняет данные в PostgreSQL и предоставляет REST API для их получения.

---

## Технологии

- Python 3.11
- FastAPI
- PostgreSQL
- SQLAlchemy
- Celery
- Redis
- aiohttp
- Docker / Docker Compose
- Pytest

---


Компоненты системы:

- **FastAPI** — внешний API
- **Celery Worker** — выполнение фоновых задач
- **Celery Beat** — планировщик задач (каждую минуту)
- **Redis** — брокер сообщений
- **PostgreSQL** — база данных
- **aiohttp** — асинхронный HTTP клиент для Deribit API

---

## Архитектура

```
Deribit API
     │
 aiohttp client
     │
 Celery Worker
     │
 PostgreSQL
     │
   FastAPI
     │
    User
```


## Работа системы

1. Celery Beat каждые **60 секунд** запускает задачу `fetch_prices`
2. Задача обращается к **Deribit API**
3. Получает:
   - btc_usd index price
   - eth_usd index price
4. Сохраняет данные в PostgreSQL:

```
ticker
price
timestamp
```

5. FastAPI предоставляет REST API для доступа к данным.

---

## API

### Получение всех цен

```
GET /prices?ticker=btc_usd
```

Ответ:

```json
[
{
"id": 1,
"ticker": "btc_usd",
"price": 65000.5,
"timestamp": 1700000000
}
]
```

---

### Получение последней цены

```
GET /price/latest?ticker=btc_usd
```

Ответ:

```json
{
"id": 10,
"ticker": "btc_usd",
"price": 65120.2,
"timestamp": 1700000123
}
```

---

### Получение цен по диапазону времени

```
GET /price/by-date?ticker=btc_usd&start=1700000000&end=1700000600
```

Ответ:

```json
[
{
"id": 2,
"ticker": "btc_usd",
"price": 65010,
"timestamp": 1700000010
}
]
```

---

## Web UI

Для удобного тестирования API доступна простая HTML страница:

```
http://localhost:8000/
```

Она позволяет:

- получить историю цен
- получить последнюю цену
- фильтровать по диапазону timestamp

---

## Установка

### Способ 1: Локальная установка

**1. Клонировать репозиторий**

```bash
git clone https://github.com/erdes10032/Deribit-client.git
cd deribit-client
```

---

**2. Создать виртуальное окружение**

```bash
python -m venv venv
source venv/bin/activate  # Linux
# или
venv\Scripts\activate  # Windows
```

---

**3. Установить зависимости**

```bash
pip install -r requirements.txt
```

---

**4. Заполнить файл .env своими данными**

---

**5. Создать таблицы**

```bash
python -m app.db.init_db
```

---

**6. Запустить FastAPI сервер**

```bash
uvicorn app.main:app --reload
```

**7. Запустить Celery worker**

```bash
celery -A app.tasks.celery_tasks.celery worker --loglevel=info
```

**8.Запустить Celery beat**

```bash
celery -A app.tasks.celery_tasks.celery beat --loglevel=info
```

### Способ 2: Docker-установка

**1. Клонировать репозиторий**

```bash
git clone https://github.com/erdes10032/Deribit-client.git
cd deribit-client
```

---

**2. Запустить проект**

```bash
docker compose up --build
```

Будут запущены контейнеры:

```
app
db
redis
worker
beat
```

---

**3. API будет доступно по адресу**

```
http://localhost:8000
```

Swagger:

```
http://localhost:8000/docs
```

---

## База данных

Структура:

| поле | тип |
|-----|----|
| id | integer |
| ticker | string |
| price | float |
| timestamp | bigint |

---

## Тесты

Запуск тестов:

```bash
pytest # Локально

docker compose exec app pytest # Через Docker
```

Тестируются:

- API методы
- Celery задача
- сохранение данных в БД

Используется:

- SQLite
- monkeypatch для mock Deribit API

---

## Design Decisions

### FastAPI

FastAPI выбран из-за:

- высокой производительности
- нативной поддержки async
- автоматической генерации OpenAPI / Swagger
- удобной интеграции с Pydantic

---

### Celery

Celery используется для:

- выполнения фоновых задач
- периодического сбора данных
- масштабируемости системы

Celery Beat запускает задачу сбора цен **раз в минуту**.

---

### Redis

Redis используется как:

- broker для Celery
- backend для хранения результатов задач

Он лёгкий и широко используется с Celery.

---

### aiohttp

aiohttp используется для:

- асинхронных HTTP запросов
- более эффективного использования соединений
- высокой производительности при работе с внешними API

---

### PostgreSQL

PostgreSQL выбран из-за:

- надёжности
- поддержки больших объёмов данных
- распространённости в production системах

---

### Docker

Docker используется для:

- воспроизводимого окружения
- простого развёртывания
- изоляции сервисов

Система запускается через `docker-compose`.

---

### Разделение на сервисы

Система разделена на несколько контейнеров:

```
API (FastAPI)
Worker (Celery)
Beat (scheduler)
PostgreSQL
Redis
```

Это позволяет:

- масштабировать воркеры
- изолировать компоненты
- повышать отказоустойчивость

---
