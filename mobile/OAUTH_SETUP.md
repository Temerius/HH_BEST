# Настройка Google OAuth для мобильного приложения

## Проблема с приватными IP-адресами

Google OAuth не принимает приватные IP-адреса (например, `192.168.x.x`) в redirect URI. Для решения этой проблемы используется сервис **nip.io**.

## Решение: Использование nip.io

### 1. Преобразование IP в домен

Используйте nip.io для преобразования приватного IP в публичный домен:

**Ваш текущий IP:** `192.168.100.4`

**Варианты домена:**
- Dash syntax: `192-168-100-4.nip.io` (рекомендуется)
- Dot syntax: `192.168.100.4.nip.io`

**Полный URL:** `http://192-168-100-4.nip.io:8000`

### 2. Обновление конфигурации приложения

В файле `lib/config/api_config.dart` уже настроен nip.io домен:
```dart
static const String baseUrl = 'http://192-168-100-4.nip.io:8000';
```

### 3. Настройка Google OAuth Console

**ВАЖНО:** Нужно обновить Redirect URI в Google Cloud Console:

1. Откройте [Google Cloud Console](https://console.cloud.google.com/)
2. Перейдите в **APIs & Services** → **Credentials**
3. Найдите ваш OAuth 2.0 Client ID
4. В разделе **Authorized redirect URIs** добавьте:
   ```
   http://192-168-100-4.nip.io:8000/api/auth/google/callback
   ```

   **Примечание:** Google Console не принимает wildcards, поэтому нужно указать полный домен с nip.io.

### 4. Проверка работы

После настройки:
- nip.io автоматически резолвит домен в ваш приватный IP
- Google OAuth будет принимать этот домен как публичный
- OAuth flow должен работать корректно

### 5. Если IP изменился

Если IP-адрес вашего компьютера изменился:
1. Обновите `baseUrl` в `lib/config/api_config.dart`
2. Обновите Redirect URI в Google Console
3. Пересоберите приложение

### Альтернативные варианты

Если nip.io не работает, можно использовать:
- **xip.io** (аналогичный сервис)
- Настройка локального DNS
- Использование ngrok или подобных туннелей

