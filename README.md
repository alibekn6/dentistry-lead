# 🦷 Dentistry Lead Generation System

Автоматическая система для поиска и вовлечения B2B-лидов премиальных стоматологий с мультиканальной email цепочкой.

## 🚀 Быстрый старт

### Одна команда - полный запуск!

```bash
git clone <your-repo-url>
cd dentistry
docker compose up --build
docker compose exec app uv run python src/main.py auto
```

**Вот и всё!** Система автоматически:
1. 📊 Инициализирует базу данных PostgreSQL
2. 🔍 Скрейпит лиды премиальных стоматологий
3. 📧 Запускает email кампанию (3 шага по 24 сек)
4. 📄 Экспортирует результаты в CSV

### 📋 Что происходит автоматически

```
🚀 Starting automated pipeline...
📊 Step 1/5: Initializing database...
📈 Step 2/5: Checking initial status...
🔍 Step 3/5: Scraping leads...
📧 Step 4/5: Running email campaign...
📄 Step 5/5: Exporting results...
🎉 Pipeline completed successfully!
```

### 📂 Результаты

- **CSV экспорт**: `./data/leads_export.csv`
- **Логи**: в консоли Docker
- **База данных**: PostgreSQL на порту 5432
- **Контейнер завершается** после выполнения задач

### 🔄 Для новых данных:
```bash
# Перезапустить для новых лидов
docker compose up --build

# Или только приложение (если БД уже запущена)
docker compose up app --build
```

### 📊 Инспекция результатов:
```bash
# Посмотреть CSV
cat ./data/leads_export.csv

# Подключиться к БД
docker compose exec db psql -U dentistry_user -d dentistry_db

# Посмотреть логи
docker compose logs app
```

## 🔧 Что делать при ошибках

### Если видите ошибку "No module named 'src'":
```bash
docker compose down
docker compose up --build
```

### Если pipeline упал с ошибкой:
```bash
# Перезапуск без пересборки
docker compose down && docker compose up

# Или полная очистка (удаляет данные БД)
docker compose down -v && docker compose up --build
```

### Посмотреть логи:
```bash
docker compose logs -f app
```

### Подключиться к контейнеру для отладки:
```bash
docker compose exec app bash
```

## 🛠️ Ручное управление

Если нужно запустить команды отдельно:

```bash
# Запустить только БД
docker compose up db -d

# Выполнить команды вручную
docker compose run --rm app uv run python src/main.py init-db
docker compose run --rm app uv run python src/main.py scrape
docker compose run --rm app uv run python src/main.py run-campaign
docker compose run --rm app uv run python src/main.py export-csv
docker compose run --rm app uv run python src/main.py status
docker compose exec app uv run python src/main.py enrich-emails
```

## ⚙️ Конфигурация

Создайте `.env` файл для настройки:

```bash
# Database
DATABASE_URL=postgresql://dentistry_user:dentistry_pass@db:5432/dentistry_db

# Email (опционально)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=your_email@gmail.com

# Campaign
SELLER_NAME=Alex
STEP_DELAY_SECONDS=24  # 24 сек для тестов, 86400 для продакшена
```

## 📊 Архитектура

- **PostgreSQL**: Хранение лидов и истории взаимодействий
- **Google Maps API**: Поиск премиальных стоматологий
- **Email SMTP**: Отправка персонализированных сообщений
- **CSV Export**: Результаты в формате ТЗ

## 🎯 Система работает с

- **География**: Лондон (Zone 1), Европа
- **Ниша**: Премиальные стоматологии
- **Продукт**: Премиальные зубные щетки
- **Каналы**: Email (WhatsApp готов к подключению)

## 🔧 Требования

- Docker & Docker Compose

---
