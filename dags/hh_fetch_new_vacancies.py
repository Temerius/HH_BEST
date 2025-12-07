"""
DAG для получения новых вакансий с HH.ru
Загружает только новые вакансии за последние 14 дней
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


def fetch_dictionaries(**context):
    """
    Загрузка справочников из HH API
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


def fetch_new_vacancies(**context):
    """
    Загрузка новых вакансий за последние 14 дней
    Загружает только новые вакансии (которых еще нет в БД)
    """
    logger.info("Starting new vacancies fetch from HH.ru")
    
    pg_hook = PostgresHook(postgres_conn_id='vacancy_postgres')
    session = get_hh_session()
    
    # Параметры поиска (можно настроить через Airflow Variables)
    search_text = Variable.get('hh_search_text', default_var='Python OR Java OR JavaScript')
    search_area = Variable.get('hh_search_area', default_var='1')  # 1 = Москва
    
    # Убираем period и date_from - они вызывают ошибки 400
    # Получаем вакансии без ограничения по периоду и фильтруем по published_at в коде
    date_threshold = datetime.now() - timedelta(days=14)
    
    # Пробуем с period=1 (минимальное значение) - возможно API требует обязательный параметр period
    # Если не работает, попробуем без text или с другим форматом
    search_params = {
        'text': search_text,
        'area': search_area,
        'per_page': 100,  # Максимум за запрос
        'page': 0,
        'period': 1  # Минимальное значение, затем фильтруем по дате в коде
    }
    
    logger.info(f"Fetching vacancies (will filter by published_at >= {date_threshold.strftime('%Y-%m-%d')})")
    logger.info(f"Request params: {search_params}")
    
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
                params=search_params,
                timeout=30
            )
            
            # Логируем детали ответа при ошибке
            if response.status_code != 200:
                logger.error(f"API returned status {response.status_code}")
                logger.error(f"Response headers: {dict(response.headers)}")
                logger.error(f"Response text: {response.text[:500]}")
                logger.error(f"Request URL: {response.url}")
                logger.error(f"Request params: {search_params}")
            
            response.raise_for_status()
            data = response.json()
            
            # Обновляем общее количество страниц
            total_pages = min(data.get('pages', 1), 20)  # HH отдаёт максимум 2000 вакансий (20 страниц по 100)
            
            # Обрабатываем вакансии на текущей странице
            for vacancy in data.get('items', []):
                try:
                    # Фильтруем по дате публикации (только последние 14 дней)
                    published_at_str = vacancy.get('published_at')
                    if published_at_str:
                        try:
                            # Парсим ISO формат даты (формат: 2025-11-12T10:30:00+0300)
                            # Берем только дату (первые 10 символов до 'T')
                            date_part = published_at_str.split('T')[0]
                            published_at = datetime.strptime(date_part, '%Y-%m-%d')
                            if published_at < date_threshold:
                                logger.debug(f"Skipping vacancy {vacancy.get('id')} - too old (published: {date_part})")
                                continue
                        except Exception as e:
                            logger.warning(f"Error parsing date {published_at_str} for vacancy {vacancy.get('id')}: {str(e)}")
                            # Если не удалось распарсить, пропускаем
                            continue
                    else:
                        # Если нет даты публикации, пропускаем
                        logger.debug(f"Skipping vacancy {vacancy.get('id')} - no published_at")
                        continue
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
                    
                    # 2. Проверяем, существует ли вакансия
                    connection = pg_hook.get_conn()
                    cursor = connection.cursor()
                    cursor.execute("SELECT id FROM vacancies.vacancies WHERE id = %s", (int(vacancy['id']),))
                    exists = cursor.fetchone() is not None
                    cursor.close()
                    connection.close()
                    
                    # Если вакансия уже существует, пропускаем (это DAG для новых)
                    if exists:
                        logger.debug(f"Vacancy {vacancy['id']} already exists, skipping")
                        continue
                    
                    # 3. Сохраняем вакансию
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
                    
                    # 4. Сохраняем профессиональные роли
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
                    
                    # 5. Сохраняем метро
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
                    new_vacancies += 1
                    
                except Exception as e:
                    logger.error(f"Error processing vacancy {vacancy.get('id')}: {str(e)}")
                    continue
            
            # Переходим к следующей странице
            search_params['page'] += 1
            
            # Пауза между запросами (HH рекомендует не больше 5 запросов в секунду)
            time.sleep(0.25)
        
        logger.info(f"Successfully processed {total_processed} new vacancies")
        
        # Сохраняем статистику в XCom
        context['ti'].xcom_push(key='vacancies_count', value=total_processed)
        context['ti'].xcom_push(key='new_vacancies', value=new_vacancies)
        
        return total_processed
        
    except Exception as e:
        logger.error(f"Error fetching vacancies: {str(e)}")
        raise


# Определение DAG
with DAG(
    'hh_fetch_new_vacancies',
    default_args=default_args,
    description='Fetch new vacancies from HH.ru (last 14 days)',
    schedule_interval='0 */6 * * *',  # Каждые 6 часов
    catchup=False,
    tags=['hh', 'fetch', 'new_vacancies'],
) as dag:
    
    # Таск 1: Загрузка справочников
    task_fetch_dictionaries = PythonOperator(
        task_id='fetch_dictionaries',
        python_callable=fetch_dictionaries,
    )
    
    # Таск 2: Загрузка новых вакансий
    task_fetch_vacancies = PythonOperator(
        task_id='fetch_new_vacancies',
        python_callable=fetch_new_vacancies,
    )
    
    # Определяем порядок выполнения
    task_fetch_dictionaries >> task_fetch_vacancies

