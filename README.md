# Deribit Client

Сервис для периодического получения цен криптовалют с биржи Deribit и предоставления API для доступа к сохранённым данным.

Приложение каждые 60 секунд получает **index price** для:

- BTC/USD
- ETH/USD
- SOL/USD
- MATIC/USD
- BNB/USD

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
- **Redis** — брокер сообщений + кеш + подписки пользователей
- **PostgreSQL** — база данных
- **aiohttp** — асинхронный HTTP клиент для Deribit API
- **Telegram Bot** — уведомления и взаимодействие с пользователями
- **AI Service** — генерация прогнозов по ценам

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
     │
 Telegram Bot
```


## Работа системы

1. Celery Beat каждые **60 секунд** запускает задачу `fetch_prices`
2. Задача обращается к **Deribit API**
3. Получает цены для нескольких валют
4. Сохраняет данные в PostgreSQL:

```
ticker
price
timestamp
```

5. Каждые 10 минут запускается задача `build_charts`:
- Строит графики по каждой валюте
- Отправляет их пользователям

6. FastAPI предоставляет REST API для доступа к данным.

7. Telegram бот позволяет управлять подписками и получать прогнозы

---

## Дополнительные возможности

### Построение графиков

Сервис автоматически:

- Строит графики цен
- Сохраняет их в папку charts
- Отображает в Web UI
- Отправляет пользователям в Telegram

---

### Подписки на валюты

Пользователь может управлять уведомлениями:

`/notification btc_usd`
- Добавляет валюту в подписки
- Повторный вызов удаляет

`/notifications`

- показывает список активных подписок

Уведомления и графики отправляются только по выбранным валютам

---

### AI прогноз цен

Сервис использует AI для анализа последних цен:
`GET /prediction?ticker=btc_usd`

AI:
- Анализирует последние значения
- Делает краткий прогноз (рост / падение)
- Объясняет причину

---

### Кеширование AI

- Ответы AI кешируются в Redis
- Уменьшает нагрузку на API
- Ускоряет повторные запросы

---

### Telegram уведомления

Система отправляет:

- Сигналы изменения цены (UP / DOWN)
- Графики цен
- Ответы AI

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

### Получение AI прогноза

```
GET /prediction?ticker=btc_usd
```

Ответ:

```json
{
  "prediction": "Ожидается рост из-за восходящего тренда..."
}
```

---

### Получение списка графиков

```
GET /charts/{filename}
```

---

### Получение изображения графика

```
GET /charts/{filename}
```

---

## Web UI

Для удобного тестирования API доступна простая HTML страница:

```
http://localhost:8000/
```

Она позволяет:

- Получить историю цен
- Получить последнюю цену
- Фильтровать по диапазону timestamp
- Получить все графики
- Сделать прогноз AI

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
celery -A app.tasks.celery_tasks.celery worker --pool=solo --loglevel=info
```

**8.Запустить Celery beat**

```bash
celery -A app.tasks.celery_tasks.celery beat --loglevel=info
```

**9. Запустить бота**

```bash
python -m app.tasks.telegram_bot
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
bot
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

### Структура таблицы prices:

| Поле      | Тип     |
|-----------|---------|
| id        | integer |
| ticker    | string  |
| price     | float   |
| timestamp | bigint  |


---

### Структура таблицы notification_subscriptions:

| Поле             | Тип     |
|------------------|---------|
| id               | integer |
| telegram_user_id | bigint  |
| ticker           | string  |

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
- Предсказания AI
- Создание полного графика

Используется:

- SQLite
- monkeypatch для mock Deribit API

---

