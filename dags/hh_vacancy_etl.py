"""
DAG для загрузки вакансий с HH.ru в PostgreSQL
Автор: kiselevas
Дата: 2025-10-26
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
HH_USER_AGENT = "VacancyMatcher/1.0 (kiselevas@example.com)"

# Параметры по умолчанию
default_args = {
    'owner': 'kiselevas',
    'depends_on_past': False,
    'start_date': datetime(2025, 10, 26),
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
        'Accept': 'application/json'
    })
    return session


def fetch_dictionaries(**context):
    """
    Таск 1: Загрузка справочников из HH API
    - Регионы (areas)
    - Профессиональные роли (professional_roles)
    """
    logger.info("Starting dictionaries fetch from HH.ru")
    
    pg_hook = PostgresHook(postgres_conn_id='vacancy_postgres')
    session = get_hh_session()
    
    stats = {
        'areas': 0,
        'professional_roles': 0
    }
    
    try:
        # 1. Загрузка регионов
        logger.info("Fetching areas...")
        response = session.get(f"{HH_API_BASE_URL}/areas")
        response.raise_for_status()
        areas_data = response.json()
        
        # Рекурсивная функция для обхода дерева регионов
        def process_areas(areas_list, parent_id=None):
            count = 0
            for area in areas_list:
                # Вставка региона
                pg_hook.run(
                    """
                    INSERT INTO vacancies.areas (id, name, parent_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO UPDATE 
                    SET name = EXCLUDED.name, parent_id = EXCLUDED.parent_id
                    """,
                    parameters=(area['id'], area['name'], parent_id)
                )
                count += 1
                
                # Обработка вложенных регионов
                if 'areas' in area and area['areas']:
                    count += process_areas(area['areas'], area['id'])
            
            return count
        
        stats['areas'] = process_areas(areas_data)
        logger.info(f"Loaded {stats['areas']} areas")
        
        # 2. Загрузка профессиональных ролей
        logger.info("Fetching professional roles...")
        response = session.get(f"{HH_API_BASE_URL}/professional_roles")
        response.raise_for_status()
        roles_data = response.json()
        
        # Обход категорий и ролей
        for category in roles_data.get('categories', []):
            for role in category.get('roles', []):
                pg_hook.run(
                    """
                    INSERT INTO vacancies.professional_roles (id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (id) DO UPDATE 
                    SET name = EXCLUDED.name
                    """,
                    parameters=(int(role['id']), role['name'])
                )
                stats['professional_roles'] += 1
        
        logger.info(f"Loaded {stats['professional_roles']} professional roles")
        
        # Сохраняем статистику в XCom
        context['ti'].xcom_push(key='dict_stats', value=stats)
        
        logger.info("Dictionaries loaded successfully")
        return stats
        
    except Exception as e:
        logger.error(f"Error loading dictionaries: {str(e)}")
        raise


def fetch_vacancies_list(**context):
    """
    Таск 2: Загрузка списка вакансий (без полного описания)
    Загружает только новые вакансии (с момента последней загрузки)
    Параметры можно настроить через Airflow Variables
    """
    logger.info("Starting vacancies list fetch from HH.ru")
    
    pg_hook = PostgresHook(postgres_conn_id='vacancy_postgres')
    session = get_hh_session()
    
    # Определяем дату последней загрузки
    connection = pg_hook.get_conn()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT MAX(fetched_at) FROM vacancies.vacancies
    """)
    last_fetch = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    
    # Если это первая загрузка, загружаем за последние 30 дней
    # Иначе загружаем только новые (с момента последней загрузки)
    if last_fetch:
        from datetime import datetime, timedelta
        # Берем дату на день раньше для надежности
        date_from = (last_fetch - timedelta(days=1)).strftime('%Y-%m-%d')
        logger.info(f"Last fetch was at {last_fetch}, loading from {date_from}")
        use_date_from = True
    else:
        date_from = None
        logger.info("First load, loading vacancies from last 30 days")
        use_date_from = False
    
    # Параметры поиска (можно настроить через Airflow Variables)
    search_params = {
        'text': Variable.get('hh_search_text', default_var='Python OR Java OR JavaScript'),
        'area': Variable.get('hh_search_area', default_var='1'),  # 1 = Москва
        'per_page': 100,  # Максимум за запрос
        'page': 0,
        'only_with_salary': False
    }
    
    # Если не первая загрузка, используем date_from вместо period
    if use_date_from:
        search_params['date_from'] = date_from
    else:
        search_params['period'] = 30  # За последние 30 дней при первой загрузке
    
    total_processed = 0
    new_vacancies = 0
    updated_vacancies = 0
    total_pages = 1
    
    try:
        while search_params['page'] < total_pages:
            logger.info(f"Fetching page {search_params['page'] + 1}/{total_pages}")
            
            # Запрос к API
            response = session.get(
                f"{HH_API_BASE_URL}/vacancies",
                params=search_params
            )
            response.raise_for_status()
            data = response.json()
            
            # Обновляем общее количество страниц
            total_pages = min(data.get('pages', 1), 20)  # HH отдаёт максимум 2000 вакансий (20 страниц по 100)
            
            # Обрабатываем вакансии на текущей странице
            for vacancy in data.get('items', []):
                try:
                    # 1. Сохраняем работодателя
                    employer = vacancy.get('employer', {})
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
                    
                    # 2. Сохраняем вакансию
                    salary = vacancy.get('salary') or {}
                    area = vacancy.get('area', {})
                    address = vacancy.get('address') or {}
                    snippet = vacancy.get('snippet', {})
                    schedule = vacancy.get('schedule', {})
                    experience = vacancy.get('experience', {})
                    employment = vacancy.get('employment', {})
                    
                    # Извлекаем первый элемент из массивов
                    work_format = vacancy.get('work_format', [{}])[0] if vacancy.get('work_format') else {}
                    working_hours = vacancy.get('working_hours', [{}])[0] if vacancy.get('working_hours') else {}
                    work_schedule = vacancy.get('work_schedule_by_days', [{}])[0] if vacancy.get('work_schedule_by_days') else {}
                    
                    # Проверяем, существует ли вакансия
                    connection = pg_hook.get_conn()
                    cursor = connection.cursor()
                    cursor.execute("SELECT id FROM vacancies.vacancies WHERE id = %s", (int(vacancy['id']),))
                    exists = cursor.fetchone() is not None
                    cursor.close()
                    connection.close()
                    
                    pg_hook.run(
                        """
                        INSERT INTO vacancies.vacancies (
                            id, name, premium, employer_id, area_id,
                            address_city, address_street, address_building, address_raw,
                            address_lat, address_lng,
                            salary_from, salary_to, salary_currency, salary_gross,
                            snippet_requirement, snippet_responsibility,
                            schedule_id, schedule_name,
                            experience_id, experience_name,
                            employment_id, employment_name,
                            work_format_id, work_format_name,
                            working_hours_id, working_hours_name,
                            work_schedule_id, work_schedule_name,
                            night_shifts,
                            has_test, response_letter_required, 
                            accept_incomplete_resumes, internship, accept_temporary,
                            url, alternate_url, apply_alternate_url,
                            published_at, created_at, archived, fetched_at
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s,
                            %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, CURRENT_TIMESTAMP
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            archived = EXCLUDED.archived,
                            salary_from = EXCLUDED.salary_from,
                            salary_to = EXCLUDED.salary_to,
                            salary_currency = EXCLUDED.salary_currency,
                            updated_at = CURRENT_TIMESTAMP,
                            fetched_at = CURRENT_TIMESTAMP
                        """,
                        parameters=(
                            int(vacancy['id']),
                            vacancy.get('name', ''),
                            vacancy.get('premium', False),
                            int(employer['id']) if employer.get('id') else None,
                            area.get('id', '1'),
                            # Адрес
                            address.get('city'),
                            address.get('street'),
                            address.get('building'),
                            address.get('raw'),
                            address.get('lat'),
                            address.get('lng'),
                            # Зарплата
                            salary.get('from'),
                            salary.get('to'),
                            salary.get('currency'),
                            salary.get('gross'),
                            # Описание
                            snippet.get('requirement'),
                            snippet.get('responsibility'),
                            # График
                            schedule.get('id'),
                            schedule.get('name'),
                            # Опыт
                            experience.get('id', 'noExperience'),
                            experience.get('name', 'Нет опыта'),
                            # Занятость
                            employment.get('id'),
                            employment.get('name'),
                            # Формат работы
                            work_format.get('id'),
                            work_format.get('name'),
                            # Рабочие часы
                            working_hours.get('id'),
                            working_hours.get('name'),
                            # График по дням
                            work_schedule.get('id'),
                            work_schedule.get('name'),
                            # Ночные смены
                            vacancy.get('night_shifts', False),
                            # Требования
                            vacancy.get('has_test', False),
                            vacancy.get('response_letter_required', False),
                            vacancy.get('accept_incomplete_resumes', False),
                            vacancy.get('internship', False),
                            vacancy.get('accept_temporary', False),
                            # Ссылки
                            vacancy.get('url'),
                            vacancy.get('alternate_url'),
                            vacancy.get('apply_alternate_url'),
                            # Даты
                            vacancy.get('published_at'),
                            vacancy.get('created_at'),
                            vacancy.get('archived', False)
                        )
                    )
                    
                    # 3. Сохраняем профессиональные роли
                    vacancy_id = int(vacancy['id'])
                    for role in vacancy.get('professional_roles', []):
                        pg_hook.run(
                            """
                            INSERT INTO vacancies.vacancy_roles (vacancy_id, role_id)
                            VALUES (%s, %s)
                            ON CONFLICT DO NOTHING
                            """,
                            parameters=(vacancy_id, int(role['id']))
                        )
                    
                    # 4. Сохраняем метро
                    metro_stations = address.get('metro_stations', [])
                    for metro in metro_stations:
                        # Сначала добавляем станцию в справочник
                        pg_hook.run(
                            """
                            INSERT INTO vacancies.metro_stations (
                                station_id, station_name, line_id, line_name, 
                                lat, lng, area_id
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (station_id) DO UPDATE 
                            SET station_name = EXCLUDED.station_name,
                                line_name = EXCLUDED.line_name
                            """,
                            parameters=(
                                metro.get('station_id'),
                                metro.get('station_name'),
                                metro.get('line_id'),
                                metro.get('line_name'),
                                metro.get('lat'),
                                metro.get('lng'),
                                area.get('id')
                            )
                        )
                        
                        # Связываем с вакансией
                        pg_hook.run(
                            """
                            INSERT INTO vacancies.vacancy_metro (vacancy_id, station_id)
                            VALUES (%s, %s)
                            ON CONFLICT DO NOTHING
                            """,
                            parameters=(vacancy_id, metro.get('station_id'))
                        )
                    
                    total_processed += 1
                    if exists:
                        updated_vacancies += 1
                    else:
                        new_vacancies += 1
                    
                except Exception as e:
                    logger.error(f"Error processing vacancy {vacancy.get('id')}: {str(e)}")
                    continue
            
            # Переходим к следующей странице
            search_params['page'] += 1
            
            # Пауза между запросами (HH рекомендует не больше 5 запросов в секунду)
            time.sleep(0.25)
        
        logger.info(f"Successfully processed {total_processed} vacancies (new: {new_vacancies}, updated: {updated_vacancies})")
        
        # Сохраняем статистику в XCom
        context['ti'].xcom_push(key='vacancies_count', value=total_processed)
        context['ti'].xcom_push(key='new_vacancies', value=new_vacancies)
        context['ti'].xcom_push(key='updated_vacancies', value=updated_vacancies)
        
        return total_processed
        
    except Exception as e:
        logger.error(f"Error fetching vacancies: {str(e)}")
        raise


def fetch_vacancy_descriptions(**context):
    """
    Таск 3: Загрузка полных описаний вакансий
    Загружает description для вакансий, где description_fetched = FALSE
    """
    logger.info("Starting vacancy descriptions fetch")
    
    pg_hook = PostgresHook(postgres_conn_id='vacancy_postgres')
    session = get_hh_session()
    
    # Лимит вакансий для обновления за один запуск (чтобы не перегрузить API)
    batch_size = int(Variable.get('hh_description_batch_size', default_var='100'))
    
    try:
        # Получаем список вакансий без полного описания
        connection = pg_hook.get_conn()
        cursor = connection.cursor()
        
        cursor.execute(
            """
            SELECT id FROM vacancies.vacancies 
            WHERE description_fetched = FALSE 
            AND archived = FALSE
            ORDER BY published_at DESC
            LIMIT %s
            """,
            (batch_size,)
        )
        
        vacancy_ids = [row[0] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        
        logger.info(f"Found {len(vacancy_ids)} vacancies to update")
        
        updated_count = 0
        
        for vacancy_id in vacancy_ids:
            try:
                # Запрос полной информации о вакансии
                response = session.get(f"{HH_API_BASE_URL}/vacancies/{vacancy_id}")
                
                if response.status_code == 404:
                    # Вакансия удалена, помечаем как архивную
                    pg_hook.run(
                        """
                        UPDATE vacancies.vacancies 
                        SET archived = TRUE, 
                            description_fetched = TRUE,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        parameters=(vacancy_id,)
                    )
                    logger.warning(f"Vacancy {vacancy_id} not found (archived)")
                    continue
                
                response.raise_for_status()
                vacancy_data = response.json()
                
                # Обновляем описание
                pg_hook.run(
                    """
                    UPDATE vacancies.vacancies 
                    SET description = %s,
                        description_fetched = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    parameters=(
                        vacancy_data.get('description'),
                        vacancy_id
                    )
                )
                
                updated_count += 1
                
                # Пауза между запросами
                time.sleep(0.25)
                
            except Exception as e:
                logger.error(f"Error fetching description for vacancy {vacancy_id}: {str(e)}")
                continue
        
        logger.info(f"Successfully updated {updated_count} vacancy descriptions")
        
        # Сохраняем статистику в XCom
        context['ti'].xcom_push(key='descriptions_updated', value=updated_count)
        
        return updated_count
        
    except Exception as e:
        logger.error(f"Error in descriptions fetch: {str(e)}")
        raise


def update_old_vacancies(**context):
    """
    Таск 4: Обновление устаревших вакансий
    Проверяет вакансии старше 7 дней и обновляет их статус
    """
    logger.info("Starting update of old vacancies")
    
    pg_hook = PostgresHook(postgres_conn_id='vacancy_postgres')
    session = get_hh_session()
    
    # Лимит вакансий для проверки за один запуск
    batch_size = int(Variable.get('hh_update_batch_size', default_var='50'))
    days_old = int(Variable.get('hh_update_days_old', default_var='7'))
    
    try:
        # Получаем список вакансий для проверки
        connection = pg_hook.get_conn()
        cursor = connection.cursor()
        
        cursor.execute(
            """
            SELECT id FROM vacancies.vacancies 
            WHERE archived = FALSE
            AND fetched_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
            ORDER BY fetched_at ASC
            LIMIT %s
            """,
            (days_old, batch_size)
        )
        
        vacancy_ids = [row[0] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        
        logger.info(f"Found {len(vacancy_ids)} old vacancies to check")
        
        updated_count = 0
        archived_count = 0
        
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
                    logger.debug(f"Vacancy {vacancy_id} archived (not found)")
                    continue
                
                response.raise_for_status()
                vacancy_data = response.json()
                
                # Проверяем, изменилась ли вакансия
                # Обновляем основные поля
                salary = vacancy_data.get('salary') or {}
                area = vacancy_data.get('area', {})
                
                pg_hook.run(
                    """
                    UPDATE vacancies.vacancies 
                    SET name = %s,
                        archived = %s,
                        salary_from = %s,
                        salary_to = %s,
                        salary_currency = %s,
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
                        vacancy_id
                    )
                )
                
                updated_count += 1
                
                # Пауза между запросами
                time.sleep(0.25)
                
            except Exception as e:
                logger.error(f"Error updating vacancy {vacancy_id}: {str(e)}")
                continue
        
        logger.info(f"Updated {updated_count} vacancies, archived {archived_count} vacancies")
        
        # Сохраняем статистику в XCom
        context['ti'].xcom_push(key='updated_old_count', value=updated_count)
        context['ti'].xcom_push(key='archived_old_count', value=archived_count)
        
        return {'updated': updated_count, 'archived': archived_count}
        
    except Exception as e:
        logger.error(f"Error updating old vacancies: {str(e)}")
        raise


def update_statistics(**context):
    """
    Таск 4: Обновление статистики и очистка старых данных
    """
    logger.info("Updating statistics")
    
    pg_hook = PostgresHook(postgres_conn_id='vacancy_postgres')
    
    try:
        # Получаем статистику из предыдущих тасков
        ti = context['ti']
        dict_stats = ti.xcom_pull(task_ids='fetch_dictionaries', key='dict_stats') or {}
        vacancies_count = ti.xcom_pull(task_ids='fetch_vacancies_list', key='vacancies_count') or 0
        new_vacancies = ti.xcom_pull(task_ids='fetch_vacancies_list', key='new_vacancies') or 0
        updated_vacancies = ti.xcom_pull(task_ids='fetch_vacancies_list', key='updated_vacancies') or 0
        descriptions_count = ti.xcom_pull(task_ids='fetch_vacancy_descriptions', key='descriptions_updated') or 0
        old_updated = ti.xcom_pull(task_ids='update_old_vacancies', key='updated_old_count') or 0
        old_archived = ti.xcom_pull(task_ids='update_old_vacancies', key='archived_old_count') or 0
        
        # Получаем общую статистику из БД
        connection = pg_hook.get_conn()
        cursor = connection.cursor()
        
        cursor.execute("SELECT * FROM vacancies.get_stats()")
        db_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Архивируем старые вакансии (старше 60 дней)
        cursor.execute(
            """
            UPDATE vacancies.vacancies 
            SET archived = TRUE 
            WHERE published_at < CURRENT_DATE - INTERVAL '60 days' 
            AND archived = FALSE
            RETURNING id
            """
        )
        archived_count = cursor.rowcount
        connection.commit()
        
        cursor.close()
        connection.close()
        
        # Формируем итоговую статистику
        stats = {
            'run_date': datetime.now().isoformat(),
            'dictionaries': dict_stats,
            'vacancies_processed': vacancies_count,
            'new_vacancies': new_vacancies,
            'updated_vacancies': updated_vacancies,
            'descriptions_updated': descriptions_count,
            'old_vacancies_updated': old_updated,
            'old_vacancies_archived': old_archived,
            'archived_old_vacancies': archived_count,
            'database_stats': db_stats
        }
        
        logger.info(f"Statistics: {stats}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error updating statistics: {str(e)}")
        raise


# Определение DAG
with DAG(
    'hh_vacancy_etl',
    default_args=default_args,
    description='ETL pipeline for loading vacancies from HH.ru to PostgreSQL',
    schedule_interval='0 2 * * *',  # Каждый день в 2:00 ночи
    catchup=False,
    tags=['hh', 'etl', 'vacancies'],
) as dag:
    
    # Таск 1: Загрузка справочников
    task_fetch_dictionaries = PythonOperator(
        task_id='fetch_dictionaries',
        python_callable=fetch_dictionaries,
        provide_context=True,
    )
    
    # Таск 2: Загрузка списка вакансий
    task_fetch_vacancies = PythonOperator(
        task_id='fetch_vacancies_list',
        python_callable=fetch_vacancies_list,
        provide_context=True,
    )
    
    # Таск 3: Загрузка полных описаний
    task_fetch_descriptions = PythonOperator(
        task_id='fetch_vacancy_descriptions',
        python_callable=fetch_vacancy_descriptions,
        provide_context=True,
    )
    
    # Таск 4: Обновление устаревших вакансий (параллельно с загрузкой описаний)
    task_update_old = PythonOperator(
        task_id='update_old_vacancies',
        python_callable=update_old_vacancies,
        provide_context=True,
    )
    
    # Таск 5: Обновление статистики
    task_update_stats = PythonOperator(
        task_id='update_statistics',
        python_callable=update_statistics,
        provide_context=True,
    )
    
    # Определяем порядок выполнения
    task_fetch_dictionaries >> task_fetch_vacancies >> [task_fetch_descriptions, task_update_old] >> task_update_stats