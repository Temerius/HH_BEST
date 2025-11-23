# Настройка переменных окружения

## Создание .env файла

1. Скопируйте `.env.example` в `.env`:
```bash
cp .env.example .env
```

2. Отредактируйте `.env` файл и заполните необходимые переменные:

### Обязательные переменные

```env
# Database
POSTGRES_USER=kiselevas
POSTGRES_PASSWORD=qwerty
POSTGRES_DB=hh_data

# JWT (обязательно измените в продакшене!)
SECRET_KEY=your-secret-key-change-in-production
REFRESH_SECRET_KEY=your-refresh-secret-key-change-in-production
```

### Опциональные переменные

#### OAuth Google (для входа через Google)
```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
FRONTEND_URL=http://localhost:3000
```

#### Redis (если используете другой Redis)
```env
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
```

#### CORS (если нужны дополнительные домены)
```env
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,https://yourdomain.com
```

#### AI Providers
```env
AI_PROVIDER=nebius
NEBius_API_KEY=your-key
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_ENDPOINT=your-endpoint
```

## Генерация секретных ключей

Для генерации безопасных SECRET_KEY и REFRESH_SECRET_KEY:

```python
import secrets
print(secrets.token_urlsafe(32))
```

Или через OpenSSL:
```bash
openssl rand -hex 32
```

## Важные замечания

1. **Никогда не коммитьте `.env` файл в репозиторий!**
   - Файл уже добавлен в `.gitignore`

2. **В продакшене обязательно:**
   - Измените все секретные ключи
   - Используйте сильные пароли для БД
   - Настройте HTTPS
   - Ограничьте CORS_ORIGINS только вашими доменами

3. **Для разных окружений:**
   - Создайте отдельные `.env` файлы: `.env.development`, `.env.production`
   - Используйте docker-compose с `--env-file` флагом

## Проверка переменных

После создания `.env` файла, перезапустите контейнеры:

```bash
docker-compose down
docker-compose up -d
```

Проверьте логи бэкенда:
```bash
docker-compose logs backend
```

Если все переменные загружены правильно, ошибок не будет.

