# Настройка Airflow Connection

После запуска Airflow необходимо настроить connection для PostgreSQL:

1. Откройте Airflow UI: http://localhost:8080
2. Войдите: admin/admin
3. Перейдите в Admin -> Connections
4. Добавьте новое connection:
   - **Connection Id**: `vacancy_postgres`
   - **Connection Type**: `Postgres`
   - **Host**: `postgres`
   - **Schema**: `hh_data`
   - **Login**: `kiselevas`
   - **Password**: `qwerty`
   - **Port**: `5432`

5. Сохраните connection

Теперь DAG `hh_vacancy_etl` сможет подключаться к базе данных.

## Настройка переменных Airflow (опционально)

Можно настроить параметры поиска вакансий через Airflow Variables:

1. Перейдите в Admin -> Variables
2. Добавьте переменные:
   - `hh_search_text`: `Python OR Java OR JavaScript` (поисковый запрос)
   - `hh_search_area`: `1` (1 = Москва, 16 = Санкт-Петербург)
   - `hh_description_batch_size`: `100` (сколько описаний загружать за раз)
   - `hh_update_batch_size`: `50` (сколько старых вакансий проверять)
   - `hh_update_days_old`: `7` (через сколько дней проверять вакансию)

