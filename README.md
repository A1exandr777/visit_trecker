
# Счётчик посещений на aiohttp с хранением данных в JSON

Простой веб-сервис на [aiohttp](https://docs.aiohttp.org/) для подсчёта общего и уникального количества посещений по IP-адресу.  
Данные хранятся в локальном `visits.json` файле без использования базы данных.

## Возможности

- Подсчёт **общего числа посещений**.
- Статистика **по дням** **по месяцам** **по годам**.
- Подсчёт **уникальных посетителей по IP**.
- Простой HTML-интерфейс и JSON API.
- Возможность сброса статистики через API.

## 🧰 Требования

- Python 3.8+
- Библиотека `aiohttp`

Установка зависимостей:
```bash
pip install aiohttp
````

## 🚀 Запуск

Сохраните код в файл `main.py`, и запустите:

```bash
python main.py
```

По умолчанию сервер стартует на `http://0.0.0.0:8080`.

## 🌐 Эндпоинты

| Метод | Путь                 | Описание                                 |
| ----- |----------------------| ---------------------------------------- |
| GET   | `/`                  | Простой HTML со статистикой              |
| GET   | `/count`             | Возвращает всю статистику в формате JSON |
| POST  | `/reset`(через curl) | Сбрасывает все счётчики                  |

### 📈 Пример ответа `/count`

```json
{
  "total": 0,
  "today": 0,
  "this_month": 0,
  "this_year": 0,
  "unique_total": 0,
  "unique_today": 0,
  "unique_this_month": 0,
  "unique_this_year": 0,
  "by_day": {

  },
  "by_month": {

  },
  "by_year": {

  },
  "unique_by_day": {

  },
  "unique_by_month": {

  },
  "unique_by_year": {

  }
}
```

### 🔄 Сброс статистики

```bash
curl -X POST http://localhost:8080/reset
```

Ответ:

```json
{"status": "ok", "message": "counters reset"}
```

## 📁 Структура данных `visits.json`

```json
{
  "total": 0,
  "by_day": {},
  "by_month": {},
  "unique_total": 0,
  "unique_by_day": {},
  "unique_by_month": {},
  "unique_ips": [],
  "by_year": {},
  "unique_by_year": {}
}
