"""
DAG для обновления существующих вакансий с HH.ru
Обновляет информацию о вакансиях, которые уже есть в БД
Автор: kiselevas
Дата: 2025-11-24
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
import requests
import logging
import time

# Настройка логирования
logger = logging.getLogger(__name__)

# Конфигурация HH API
HH_API_BASE_URL = "https://api.hh.ru"
# Используем User-Agent реального браузера, чтобы избежать блокировки
HH_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Параметры по умолчанию
default_args = {
    'owner': 'kiselevas',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 24),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}


def get_hh_session():
    """Создаёт HTTP сессию с правильными заголовками для HH API"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': HH_USER_AGENT,
        'Accept': 'application/json',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://hh.ru/'
    })
    return session


def update_existing_vacancies(**context):
    """
    Обновление существующих вакансий
    Проверяет вакансии, которые были загружены ранее, и обновляет их данные
    """
    logger.info("Starting update of existing vacancies")
    
    pg_hook = PostgresHook(postgres_conn_id='vacancy_postgres')
    session = get_hh_session()
    
    # Лимит вакансий для обновления за один запуск
    batch_size = int(Variable.get('hh_update_batch_size', default_var='100'))
    # Обновляем вакансии, которые были загружены более 1 дня назад
    days_old = int(Variable.get('hh_update_days_old', default_var='1'))
    
    try:
        # Получаем список вакансий для обновления (не архивные, загружены более N дней назад)
        connection = pg_hook.get_conn()
        cursor = connection.cursor()
        
        cursor.execute(
            """
            SELECT id FROM vacancies.vacancies 
            WHERE archived = FALSE
            AND fetched_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
            AND published_at >= CURRENT_DATE - INTERVAL '14 days'
            ORDER BY fetched_at ASC
            LIMIT %s
            """,
            (days_old, batch_size)
        )
        
        vacancy_ids = [row[0] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        
        logger.info(f"Found {len(vacancy_ids)} vacancies to update")
        
        updated_count = 0
        archived_count = 0
        not_found_count = 0
        
        for vacancy_id in vacancy_ids:
            try:
                # Запрос информации о вакансии
                response = session.get(f"{HH_API_BASE_URL}/vacancies/{vacancy_id}")
                
                if response.status_code == 404:
                    # Вакансия удалена, помечаем как архивную
                    pg_hook.run(
                        """
                        UPDATE vacancies.vacancies 
                        SET archived = TRUE, 
                            updated_at = CURRENT_TIMESTAMP,
                            fetched_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        parameters=(vacancy_id,)
                    )
                    archived_count += 1
                    not_found_count += 1
                    logger.debug(f"Vacancy {vacancy_id} archived (not found)")
                    continue
                
                response.raise_for_status()
                vacancy_data = response.json()
                
                # Обновляем данные вакансии
                salary = vacancy_data.get('salary') or {}
                area = vacancy_data.get('area', {})
                address = vacancy_data.get('address') or {}
                snippet = vacancy_data.get('snippet', {})
                schedule = vacancy_data.get('schedule', {})
                experience = vacancy_data.get('experience', {})
                employment = vacancy_data.get('employment', {})
                
                # Извлекаем первый элемент из массивов
                work_format = vacancy_data.get('work_format', [{}])[0] if vacancy_data.get('work_format') else {}
                working_hours = vacancy_data.get('working_hours', [{}])[0] if vacancy_data.get('working_hours') else {}
                work_schedule = vacancy_data.get('work_schedule_by_days', [{}])[0] if vacancy_data.get('work_schedule_by_days') else {}
                
                pg_hook.run(
                    """
                    UPDATE vacancies.vacancies 
                    SET name = %s,
                        archived = %s,
                        salary_from = %s,
                        salary_to = %s,
                        salary_currency = %s,
                        snippet_requirement = %s,
                        snippet_responsibility = %s,
                        schedule_id = %s,
                        schedule_name = %s,
                        experience_id = %s,
                        experience_name = %s,
                        employment_id = %s,
                        employment_name = %s,
                        work_format_id = %s,
                        work_format_name = %s,
                        working_hours_id = %s,
                        working_hours_name = %s,
                        work_schedule_id = %s,
                        work_schedule_name = %s,
                        updated_at = CURRENT_TIMESTAMP,
                        fetched_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    parameters=(
                        vacancy_data.get('name', ''),
                        vacancy_data.get('archived', False),
                        salary.get('from'),
                        salary.get('to'),
                        salary.get('currency'),
                        snippet.get('requirement'),
                        snippet.get('responsibility'),
                        schedule.get('id'),
                        schedule.get('name'),
                        experience.get('id', 'noExperience'),
                        experience.get('name', 'Нет опыта'),
                        employment.get('id'),
                        employment.get('name'),
                        work_format.get('id'),
                        work_format.get('name'),
                        working_hours.get('id'),
                        working_hours.get('name'),
                        work_schedule.get('id'),
                        work_schedule.get('name'),
                        vacancy_id
                    )
                )
                
                # Обновляем работодателя
                employer = vacancy_data.get('employer', {})
                if employer.get('id'):
                    pg_hook.run(
                        """
                        INSERT INTO vacancies.employers (id, name, trusted, accredited_it_employer)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE 
                        SET name = EXCLUDED.name,
                            trusted = EXCLUDED.trusted,
                            accredited_it_employer = EXCLUDED.accredited_it_employer,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        parameters=(
                            int(employer['id']),
                            employer.get('name', 'Unknown'),
                            employer.get('trusted', False),
                            employer.get('accredited_it_employer', False)
                        )
                    )
                
                updated_count += 1
                
                # Пауза между запросами
                time.sleep(0.25)
                
            except Exception as e:
                logger.error(f"Error updating vacancy {vacancy_id}: {str(e)}")
                continue
        
        logger.info(f"Updated {updated_count} vacancies, archived {archived_count} vacancies (not found: {not_found_count})")
        
        # Сохраняем статистику в XCom
        context['ti'].xcom_push(key='updated_count', value=updated_count)
        context['ti'].xcom_push(key='archived_count', value=archived_count)
        context['ti'].xcom_push(key='not_found_count', value=not_found_count)
        
        return {'updated': updated_count, 'archived': archived_count, 'not_found': not_found_count}
        
    except Exception as e:
        logger.error(f"Error updating existing vacancies: {str(e)}")
        raise


# Определение DAG
with DAG(
    'hh_update_existing_vacancies',
    default_args=default_args,
    description='Update existing vacancies from HH.ru',
    schedule_interval='0 */12 * * *',  # Каждые 12 часов
    catchup=False,
    tags=['hh', 'update', 'existing_vacancies'],
) as dag:
    
    # Таск: Обновление существующих вакансий
    task_update_vacancies = PythonOperator(
        task_id='update_existing_vacancies',
        python_callable=update_existing_vacancies,
    )

