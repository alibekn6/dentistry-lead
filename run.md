# 🛠️ Команды для запуска и отладки

## 🚀 Первый запуск / После изменений в коде
```bash
docker compose up --build
```

## 🔄 Перезапуск после ошибок (без пересборки)
```bash
# Остановить всё
docker compose down

# Запустить заново
docker compose up
```

## 🗑️ Полная очистка (если что-то сломалось)
```bash
# Остановить и удалить всё (включая данные БД)
docker compose down -v

# Пересобрать и запустить с нуля
docker compose up --build
```

## 🔍 Отладка

### Посмотреть логи
```bash
# Все логи
docker compose logs

# Только приложение
docker compose logs app

# Только база данных
docker compose logs db

# Следить за логами в реальном времени
docker compose logs -f app
```

### Подключиться к контейнеру
```bash
# Войти в контейнер приложения
docker compose exec app bash

# Выполнить команду вручную
docker compose exec app uv run python src/main.py status
```

### Подключиться к базе данных
```bash
# Через контейнер
docker compose exec db psql -U dentistry_user -d dentistry_db

# Проверить таблицы
\dt

# Посмотреть лиды
SELECT * FROM leads;
```

## 🎯 Быстрые фиксы

### Если модуль не найден
```bash
docker compose down
docker compose up --build
```

### Если база данных не готова
```bash
# Проверить здоровье БД
docker compose ps
docker compose logs db

# Перезапустить БД
docker compose restart db
```

### Если нужно только пересоздать таблицы
```bash
docker compose exec app uv run python src/main.py reset-db
docker compose exec app uv run python src/main.py init-db
```

## ⚡ Рекомендации

1. **После изменений в коде**: `docker compose up --build`
2. **После ошибок выполнения**: `docker compose down && docker compose up`
3. **После проблем с БД**: `docker compose down -v && docker compose up --build`
4. **Для отладки**: используйте `docker compose logs -f app`
