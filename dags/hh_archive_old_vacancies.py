"""
DAG для архивирования старых вакансий
Архивирует вакансии старше 14 дней
Автор: kiselevas
Дата: 2025-11-24
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

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


def archive_old_vacancies(**context):
    """
    Архивирование старых вакансий
    Архивирует вакансии, которые были опубликованы более 14 дней назад
    """
    logger.info("Starting archiving of old vacancies")
    
    pg_hook = PostgresHook(postgres_conn_id='vacancy_postgres')
    
    # Количество дней для архивирования (14 дней)
    days_threshold = int(Variable.get('hh_archive_days_threshold', default_var='14'))
    
    try:
        connection = pg_hook.get_conn()
        cursor = connection.cursor()
        
        # Архивируем вакансии старше N дней
        cursor.execute(
            """
            UPDATE vacancies.vacancies 
            SET archived = TRUE,
                updated_at = CURRENT_TIMESTAMP
            WHERE published_at < CURRENT_DATE - INTERVAL '%s days' 
            AND archived = FALSE
            RETURNING id
            """,
            (days_threshold,)
        )
        
        archived_ids = cursor.fetchall()
        archived_count = len(archived_ids)
        connection.commit()
        
        cursor.close()
        connection.close()
        
        logger.info(f"Archived {archived_count} old vacancies (older than {days_threshold} days)")
        
        # Сохраняем статистику в XCom
        context['ti'].xcom_push(key='archived_count', value=archived_count)
        
        return archived_count
        
    except Exception as e:
        logger.error(f"Error archiving old vacancies: {str(e)}")
        raise


# Определение DAG
with DAG(
    'hh_archive_old_vacancies',
    default_args=default_args,
    description='Archive old vacancies (older than 14 days)',
    schedule_interval='0 3 * * *',  # Каждый день в 3:00 ночи
    catchup=False,
    tags=['hh', 'archive', 'old_vacancies'],
) as dag:
    
    # Таск: Архивирование старых вакансий
    task_archive_vacancies = PythonOperator(
        task_id='archive_old_vacancies',
        python_callable=archive_old_vacancies,
    )

