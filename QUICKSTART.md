# Быстрый старт

## Предварительные требования

- Docker и Docker Compose установлены
- Порты 3000, 8000, 5432, 8080 свободны

## Запуск проекта

1. **Клонируйте репозиторий** (если еще не сделано)

2. **Создайте .env файл**:
```bash
cp .env.example .env
```
Затем отредактируйте `.env` и заполните необходимые переменные (см. [ENV_SETUP.md](ENV_SETUP.md))

3. **Запустите все сервисы**:
```bash
docker-compose up -d
```

3. **Дождитесь инициализации** (может занять несколько минут):
   - PostgreSQL создаст базу данных и применит миграции
   - Airflow инициализируется
   - Backend и Frontend запустятся

4. **Настройте Airflow Connection** (см. AIRFLOW_SETUP.md):
   - Откройте http://localhost:8080
   - Войдите: admin/admin
   - Добавьте connection `vacancy_postgres` для PostgreSQL

5. **Проверьте доступность сервисов**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Airflow: http://localhost:8080

## Первые шаги

1. **Зарегистрируйтесь** на платформе через Frontend
2. **Просмотрите вакансии** - они будут загружены через ETL процесс
3. **Добавьте вакансии в избранное**
4. **Создайте резюме** в профиле

## Запуск ETL процесса

ETL процесс запускается автоматически каждый день в 2:00 ночи.

Для ручного запуска:
1. Откройте Airflow UI: http://localhost:8080
2. Найдите DAG `hh_vacancy_etl`
3. Нажмите "Play" для запуска

## Остановка проекта

```bash
docker-compose down
```

## Очистка данных (⚠️ удалит все данные)

```bash
docker-compose down -v
```

## Проблемы и решения

### Backend не подключается к БД
- Убедитесь, что PostgreSQL запущен: `docker-compose ps`
- Проверьте логи: `docker-compose logs postgres`

### Frontend не видит Backend
- Проверьте, что Backend запущен: `docker-compose ps`
- Проверьте переменную окружения `VITE_API_URL` в docker-compose.yaml

### Миграции не применяются
- Удалите volume PostgreSQL и пересоздайте: `docker-compose down -v && docker-compose up -d`

### Airflow DAG не запускается
- Убедитесь, что connection `vacancy_postgres` настроен (см. AIRFLOW_SETUP.md)
- Проверьте логи: `docker-compose logs airflow-scheduler`

