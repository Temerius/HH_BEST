# Настройка OAuth через Google

## Шаги настройки

### 1. Создание OAuth приложения в Google Cloud Console

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Перейдите в **APIs & Services** → **Credentials**
4. Нажмите **Create Credentials** → **OAuth client ID**
5. Если это первый раз, настройте OAuth consent screen:
   - Выберите **External** (для тестирования)
   - Заполните обязательные поля (App name, User support email, Developer contact)
   - Сохраните и продолжите
6. Создайте OAuth Client ID:
   - Application type: **Web application**
   - Name: HAHABEST
   - Authorized redirect URIs:
     - `http://localhost:8000/api/auth/google/callback` (для разработки)
     - `https://yourdomain.com/api/auth/google/callback` (для продакшена)
7. Сохраните **Client ID** и **Client Secret**

### 2. Настройка переменных окружения

Добавьте в `.env` файл или в `docker-compose.yaml`:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
FRONTEND_URL=http://localhost:3000
```

### 3. Обновление docker-compose.yaml

Добавьте переменные окружения в секцию `backend`:

```yaml
backend:
  environment:
    # ... другие переменные
    GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
    GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
    FRONTEND_URL: ${FRONTEND_URL:-http://localhost:3000}
```

### 4. Перезапуск сервисов

```bash
docker-compose restart backend
```

### 5. Тестирование

1. Откройте фронтенд: http://localhost:3000
2. Перейдите на страницу входа
3. Нажмите "Войти через Google"
4. Авторизуйтесь через Google
5. Вы будете перенаправлены обратно с токенами

## Безопасность

- **Никогда не коммитьте** Client Secret в репозиторий
- Используйте переменные окружения или секреты
- Для продакшена используйте HTTPS
- Ограничьте Authorized redirect URIs только вашими доменами

## Troubleshooting

### Ошибка "redirect_uri_mismatch"
- Убедитесь, что redirect URI в Google Console точно совпадает с тем, что используется в коде
- Проверьте, что используется правильный протокол (http/https)

### Ошибка "invalid_client"
- Проверьте, что Client ID и Client Secret правильно скопированы
- Убедитесь, что переменные окружения установлены

### OAuth не работает после перезапуска
- Проверьте, что переменные окружения загружены
- Убедитесь, что Redis доступен (для хранения сессий)

