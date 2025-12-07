"""
DAG для обновления существующих вакансий с rabota.by
Обновляет информацию о вакансиях, которые уже есть в БД
Автор: kiselevas
Дата: 2025-11-27
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
import requests
import logging
import time
import re
from bs4 import BeautifulSoup

# Настройка логирования
logger = logging.getLogger(__name__)

# Конфигурация Rabota.by
RABOTA_BASE_URL = "https://rabota.by"
RABOTA_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

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


def get_rabota_session():
    """Создаёт HTTP сессию с правильными заголовками для Rabota.by"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': RABOTA_USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,be;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://rabota.by/',
        'Upgrade-Insecure-Requests': '1'
    })
    return session


def parse_vacancy_page(session, vacancy_url):
    """
    Парсит страницу вакансии для получения полной информации
    """
    try:
        response = session.get(vacancy_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        result = {
            'description': '',
            'tasks': '',
            'requirements': '',
            'advantages': '',
            'offers': '',
            'skills': []
        }
        
        # Парсим основные блоки используя правильный селектор
        description_block = soup.select_one("div.g-user-content")
        if description_block:
            result['description'] = description_block.get_text(separator='\n', strip=True)
        
        # Ищем блоки по тексту
        for text_pattern, key in [
            (r'Задачи|Обязанности', 'tasks'),
            (r'Мы ожидаем|Требования', 'requirements'),
            (r'Будет плюсом|Преимущества', 'advantages'),
            (r'Мы предлагаем|Условия', 'offers')
        ]:
            block = soup.find(text=re.compile(text_pattern, re.I))
            if block:
                parent = block.find_parent()
                if parent:
                    result[key] = parent.get_text(strip=True)
        
        # Ищем навыки
        skills_blocks = soup.find_all('span', class_=re.compile(r'skill|tag|badge', re.I))
        for skill_block in skills_blocks:
            skill_text = skill_block.get_text(strip=True)
            if skill_text:
                result['skills'].append(skill_text)
        
        # Парсим опыт работы - ищем в различных местах страницы
        experience_id = 'noExperience'
        experience_name = 'Нет опыта'
        
        # Вариант 1: Ищем через data-qa атрибуты
        experience_selectors = [
            "span[data-qa='vacancy-serp__vacancy-work-experience-noExperience']",
            "span[data-qa='vacancy-serp__vacancy-work-experience-between1And3']",
            "span[data-qa='vacancy-serp__vacancy-work-experience-between3And6']",
            "span[data-qa='vacancy-serp__vacancy-work-experience-moreThan6']",
            "span[data-qa*='vacancy-work-experience']"
        ]
        
        for selector in experience_selectors:
            exp_elem = soup.select_one(selector)
            if exp_elem:
                exp_text = exp_elem.get_text(strip=True).lower()
                # Определяем experience_id по тексту или data-qa атрибуту
                if 'noExperience' in selector or 'не требуется' in exp_text or 'без опыта' in exp_text:
                    experience_id = 'noExperience'
                    experience_name = 'Нет опыта'
                elif 'between1And3' in selector or ('1' in exp_text and '3' in exp_text):
                    experience_id = 'between1And3'
                    experience_name = 'От 1 года до 3 лет'
                elif 'between3And6' in selector or ('3' in exp_text and '6' in exp_text):
                    experience_id = 'between3And6'
                    experience_name = 'От 3 до 6 лет'
                elif 'moreThan6' in selector or 'более' in exp_text or '6+' in exp_text:
                    experience_id = 'moreThan6'
                    experience_name = 'Более 6 лет'
                break
        
        # Вариант 2: Если не нашли через селекторы, ищем в тексте
        if experience_id == 'noExperience':
            experience_text = ''
            experience_patterns = [
                r'Опыт работы[:\s]+([^<\n]+)',
                r'Требуемый опыт[:\s]+([^<\n]+)',
                r'Опыт[:\s]+([^<\n]+)'
            ]
            for pattern in experience_patterns:
                match = re.search(pattern, soup.get_text(), re.IGNORECASE)
                if match:
                    experience_text = match.group(1).strip()
                    break
            
            if experience_text:
                experience_lower = experience_text.lower()
                if 'не требуется' in experience_lower or 'без опыта' in experience_lower or 'нет опыта' in experience_lower:
                    experience_id = 'noExperience'
                    experience_name = 'Нет опыта'
                elif 'от 1' in experience_lower or '1 год' in experience_lower or '1-3' in experience_lower:
                    experience_id = 'between1And3'
                    experience_name = 'От 1 года до 3 лет'
                elif 'от 3' in experience_lower or '3-6' in experience_lower or '3 года' in experience_lower:
                    experience_id = 'between3And6'
                    experience_name = 'От 3 до 6 лет'
                elif 'более' in experience_lower or 'от 6' in experience_lower or '6+' in experience_lower:
                    experience_id = 'moreThan6'
                    experience_name = 'Более 6 лет'
        
        result['experience_id'] = experience_id
        result['experience_name'] = experience_name
        
        return result
        
    except Exception as e:
        logger.error(f"Error parsing vacancy page {vacancy_url}: {str(e)}")
        return None


def update_existing_vacancies(**context):
    """
    Обновление существующих вакансий
    Загружает полную информацию о вакансиях, которые уже есть в БД
    """
    logger.info("Starting existing vacancies update from rabota.by")
    
    pg_hook = PostgresHook(postgres_conn_id='vacancy_postgres')
    session = get_rabota_session()
    
    # Лимит вакансий для обновления за один запуск
    batch_size = int(Variable.get('rabota_update_batch_size', default_var='100'))
    
    try:
        # Получаем список вакансий для обновления
        connection = pg_hook.get_conn()
        cursor = connection.cursor()
        
        cursor.execute(
            """
            SELECT id, url FROM vacancies.vacancies 
            WHERE archived = FALSE
            AND (description_fetched = FALSE OR updated_at < NOW() - INTERVAL '7 days')
            ORDER BY published_at DESC
            LIMIT %s
            """,
            (batch_size,)
        )
        
        vacancies_to_update = cursor.fetchall()
        cursor.close()
        connection.close()
        
        updated_count = 0
        failed_count = 0
        
        for vacancy_id, vacancy_url in vacancies_to_update:
            try:
                # Если нет URL, формируем его
                if not vacancy_url:
                    vacancy_url = f"{RABOTA_BASE_URL}/vacancy/{vacancy_id}"
                
                # Нормализуем URL - убираем дублирование базового URL
                if vacancy_url.startswith('http://') or vacancy_url.startswith('https://'):
                    # Уже полный URL, проверяем на дублирование
                    if 'rabota.byhttps://' in vacancy_url or 'rabota.byhttp://' in vacancy_url:
                        # Убираем дублирование
                        vacancy_url = vacancy_url.replace('rabota.byhttps://', 'https://')
                        vacancy_url = vacancy_url.replace('rabota.byhttp://', 'http://')
                elif vacancy_url.startswith('/'):
                    # Относительный URL
                    vacancy_url = RABOTA_BASE_URL + vacancy_url
                else:
                    # Относительный URL без слэша
                    vacancy_url = f"{RABOTA_BASE_URL}/{vacancy_url}"
                
                # Парсим страницу вакансии
                vacancy_data = parse_vacancy_page(session, vacancy_url)
                
                if not vacancy_data:
                    logger.warning(f"Could not parse vacancy {vacancy_id}")
                    failed_count += 1
                    continue
                
                # Получаем опыт работы из распарсенных данных
                experience_id = vacancy_data.get('experience_id', 'noExperience')
                experience_name = vacancy_data.get('experience_name', 'Нет опыта')
                
                # Обновляем вакансию в БД
                pg_hook.run(
                    """
                    UPDATE vacancies.vacancies 
                    SET description = %s,
                        tasks = %s,
                        requirements = %s,
                        advantages = %s,
                        offers = %s,
                        experience_id = %s,
                        experience_name = %s,
                        description_fetched = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    parameters=(
                        vacancy_data.get('description', ''),
                        vacancy_data.get('tasks', ''),
                        vacancy_data.get('requirements', ''),
                        vacancy_data.get('advantages', ''),
                        vacancy_data.get('offers', ''),
                        experience_id,
                        experience_name,
                        vacancy_id
                    )
                )
                
                # Обновляем навыки
                # Сначала удаляем старые
                pg_hook.run(
                    "DELETE FROM vacancies.vacancy_skills WHERE vacancy_id = %s",
                    parameters=(vacancy_id,)
                )
                
                # Добавляем новые
                for skill in vacancy_data.get('skills', []):
                    if skill:
                        pg_hook.run(
                            """
                            INSERT INTO vacancies.vacancy_skills (vacancy_id, skill_name)
                            VALUES (%s, %s)
                            ON CONFLICT (vacancy_id, skill_name) DO NOTHING
                            """,
                            parameters=(vacancy_id, skill)
                        )
                
                updated_count += 1
                
                # Пауза между запросами
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error updating vacancy {vacancy_id}: {str(e)}")
                failed_count += 1
                continue
        
        logger.info(f"Successfully updated {updated_count} vacancies, failed: {failed_count}")
        
        context['ti'].xcom_push(key='updated_count', value=updated_count)
        context['ti'].xcom_push(key='failed_count', value=failed_count)
        
        return updated_count
        
    except Exception as e:
        logger.error(f"Error updating vacancies: {str(e)}")
        raise


# Создание DAG
dag = DAG(
    'rabota_update_existing_vacancies',
    default_args=default_args,
    description='Обновление существующих вакансий с rabota.by',
    schedule_interval=timedelta(hours=12),  # Каждые 12 часов
    catchup=False,
    tags=['rabota', 'vacancies', 'update']
)

# Задача
update_vacancies_task = PythonOperator(
    task_id='update_existing_vacancies',
    python_callable=update_existing_vacancies,
    dag=dag
)
