"""
DAG для архивирования старых вакансий с rabota.by
Архивирует вакансии старше 14 дней
Автор: kiselevas
Дата: 2025-11-27
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
    'start_date': datetime(2025, 11, 27),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}


def archive_old_vacancies(**context):
    """
    Архивирование вакансий старше 14 дней
    """
    logger.info("Starting old vacancies archiving")
    
    pg_hook = PostgresHook(postgres_conn_id='vacancy_postgres')
    
    # Дата для архивирования (старше 14 дней)
    archive_date = datetime.now() - timedelta(days=14)
    
    try:
        # Архивируем вакансии старше 14 дней
        result = pg_hook.run(
            """
            UPDATE vacancies.vacancies 
            SET archived = TRUE,
                updated_at = CURRENT_TIMESTAMP
            WHERE archived = FALSE
            AND published_at < %s
            """,
            parameters=(archive_date,)
        )
        
        # Получаем количество архивированных вакансий
        connection = pg_hook.get_conn()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM vacancies.vacancies 
            WHERE archived = TRUE
            AND updated_at >= %s
            """,
            (archive_date,)
        )
        archived_count = cursor.fetchone()[0]
        cursor.close()
        connection.close()
        
        logger.info(f"Successfully archived {archived_count} old vacancies")
        
        # Сохраняем статистику в XCom
        context['ti'].xcom_push(key='archived_count', value=archived_count)
        
        return archived_count
        
    except Exception as e:
        logger.error(f"Error archiving vacancies: {str(e)}")
        raise


# Создание DAG
dag = DAG(
    'rabota_archive_old_vacancies',
    default_args=default_args,
    description='Архивирование старых вакансий с rabota.by',
    schedule_interval=timedelta(days=1),  # Раз в день
    catchup=False,
    tags=['rabota', 'vacancies', 'archive']
)

# Задача
archive_vacancies_task = PythonOperator(
    task_id='archive_old_vacancies',
    python_callable=archive_old_vacancies,
    dag=dag
)

