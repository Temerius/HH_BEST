"""
DAG для получения новых вакансий с rabota.by
Полная версия с исправлениями
Автор: kiselevas
Дата: 2025-12-07
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
import requests
import logging
import time
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from dateutil import parser as date_parser

# Настройка логирования
logger = logging.getLogger(__name__)

# Конфигурация Rabota.by
RABOTA_BASE_URL = "https://rabota.by"
RABOTA_SEARCH_URL = f"{RABOTA_BASE_URL}/search/vacancy"
RABOTA_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Месяцы для парсинга русских дат
MONTHS_RU = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
    'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
    'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
}

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
        'Accept-Language': 'ru-RU,ru;q=0.9,be;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://rabota.by/',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    })
    return session


def parse_russian_date(date_text: str) -> datetime:
    """Парсинг русских дат типа '30 ноября 2024'"""
    try:
        if not date_text:
            return datetime.now()
        
        # Убираем лишний текст
        date_text = re.sub(
            r'(Размещено|Опубликовано|вакансия размещена|обновлена)\s*',
            '', 
            date_text, 
            flags=re.I
        ).strip()
        
        # Если ISO формат
        if 'T' in date_text:
            return date_parser.parse(date_text)
        
        # Особые случаи
        if 'сегодня' in date_text.lower():
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif 'вчера' in date_text.lower():
            return (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Парсим русский формат "30 ноября 2024" или "30 ноября"
        for month_ru, month_num in MONTHS_RU.items():
            if month_ru in date_text.lower():
                # Ищем день
                day_match = re.search(r'(\d{1,2})', date_text)
                if day_match:
                    day = int(day_match.group(1))
                    
                    # Ищем год
                    year_match = re.search(r'(\d{4})', date_text)
                    if year_match:
                        year = int(year_match.group(1))
                    else:
                        # Если нет года, используем текущий
                        year = datetime.now().year
                    
                    try:
                        return datetime(year, month_num, day)
                    except ValueError:
                        pass
                break
        
        # Пробуем dateutil parser как последний вариант
        return date_parser.parse(date_text, dayfirst=True)
        
    except Exception as e:
        logger.debug(f"Could not parse date '{date_text}': {e}")
        return datetime.now()


def extract_json_ld(soup: BeautifulSoup) -> Optional[Dict]:
    """Извлечение структурированных данных JSON-LD"""
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data:
                    if item.get('@type') == 'JobPosting':
                        return item
            elif data.get('@type') == 'JobPosting':
                return data
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


def extract_key_skills_from_page(html: str) -> List[str]:
    """Извлечение ключевых навыков из JSON данных страницы"""
    key_skills = []
    
    patterns = [
        r'"keySkills":\s*{[^}]*"keySkill":\s*\[([^\]]+)\]',
        r'"keySkill":\s*\[([^\]]+)\]',
        r'"key_skills":\s*\[([^\]]+)\]',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                skills_str = match.group(1)
                skills = re.findall(r'"([^"]+)"', skills_str)
                key_skills.extend(skills)
                if key_skills:
                    logger.debug(f"Found {len(key_skills)} key skills from page data")
                    return key_skills
            except Exception as e:
                logger.debug(f"Error extracting skills: {e}")
    
    return key_skills


def parse_complex_address(address_text: str) -> Dict[str, Any]:
    """Парсинг адреса на составляющие"""
    result = {
        'city': None,
        'street': None,
        'building': None,
        'metro_stations': []
    }
    
    if not address_text:
        return result
    
    parts = [p.strip() for p in re.split(r'[,;]', address_text) if p.strip()]
    
    if not parts:
        return result
    
    # Город слева
    city_keywords = ['Минск', 'Брест', 'Витебск', 'Гомель', 'Гродно', 'Могилев', 'Бобруйск', 'Барановичи', 'Пинск']
    if parts and any(keyword in parts[0] for keyword in city_keywords):
        result['city'] = parts[0]
        parts = parts[1:]
    
    if not parts:
        return result
    
    # Здание и улица справа
    if parts:
        last_part = parts[-1]
        if re.search(r'\d+[а-яa-z]?\d*|к\d+|корпус\s*\d+|стр\s*\d+|д\.\s*\d+', last_part, re.IGNORECASE):
            result['building'] = last_part
            parts = parts[:-1]
    
    if parts:
        last_part = parts[-1]
        street_keywords = ['улица', 'ул.', 'проспект', 'пр.', 'пр-т', 'переулок', 'пер.', 
                         'площадь', 'пл.', 'бульвар', 'б-р', 'проезд', 'шоссе', 
                         'набережная', 'наб.', 'тракт']
        if any(keyword in last_part.lower() for keyword in street_keywords):
            result['street'] = last_part
            parts = parts[:-1]
    
    # Всё остальное - метро
    for part in parts:
        clean_station = re.sub(r'(?:^|\s)(?:м\.|метро|ст\.м\.|станция метро)\s*', '', part, flags=re.IGNORECASE)
        clean_station = clean_station.strip()
        if clean_station:
            result['metro_stations'].append(clean_station)
    
    return result


def extract_coordinates(soup: BeautifulSoup) -> tuple:
    """Извлечение координат"""
    lat, lng = None, None
    
    # В data-атрибутах
    map_container = soup.find(attrs={'data-latitude': True, 'data-longitude': True})
    if map_container:
        try:
            lat = float(map_container.get('data-latitude'))
            lng = float(map_container.get('data-longitude'))
        except (ValueError, TypeError):
            pass
    
    # В JavaScript
    if not lat:
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                patterns = [r'"latitude":\s*([\d.]+)', r'"lat":\s*([\d.]+)']
                for pattern in patterns:
                    lat_match = re.search(pattern, script.string)
                    if lat_match:
                        lng_pattern = pattern.replace('lat', 'lng').replace('latitude', 'longitude')
                        lng_match = re.search(lng_pattern, script.string)
                        if lng_match:
                            try:
                                lat = float(lat_match.group(1))
                                lng = float(lng_match.group(1))
                                break
                            except ValueError:
                                continue
                if lat:
                    break
    
    return lat, lng


def parse_salary(element) -> Optional[Dict]:
    """Парсинг зарплаты"""
    if not element:
        return None
    
    text = element.get_text(strip=True) if hasattr(element, 'get_text') else str(element)
    
    numbers = re.findall(r'(\d+(?:\s?\d{3})*)', text)
    numbers = [int(n.replace(' ', '').replace('\xa0', '')) for n in numbers if n]
    
    result = {'from': None, 'to': None, 'currency': 'BYN', 'gross': False}
    
    if numbers:
        if len(numbers) >= 2:
            result['from'] = numbers[0]
            result['to'] = numbers[1]
        elif 'от' in text.lower():
            result['from'] = numbers[0]
        elif 'до' in text.lower():
            result['to'] = numbers[0]
        else:
            result['from'] = numbers[0]
            result['to'] = numbers[0]
    
    if 'USD' in text or '$' in text:
        result['currency'] = 'USD'
    elif 'EUR' in text or '€' in text:
        result['currency'] = 'EUR'
    
    result['gross'] = 'до вычета' in text.lower() or 'gross' in text.lower()
    result['description'] = text
    
    return result


def parse_vacancy_page(session, vacancy_url):
    """Парсит страницу вакансии с улучшенным парсингом даты"""
    try:
        response = session.get(vacancy_url, timeout=30)
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'description_html': '',
            'description_text': '',
            'key_skills': [],
            'salary': None,
            'experience_id': 'noExperience',
            'experience_name': 'Нет опыта',
            'employment_id': 'full',
            'employment_name': 'Полная занятость',
            'schedule_id': 'fullDay',
            'schedule_name': 'Полный день',
            'address_raw': None,
            'address_city': None,
            'address_street': None,
            'address_building': None,
            'coordinates': {'lat': None, 'lng': None},
            'metro_stations': [],
            'employer_name': None,
            'employer_url': None,
            'employer_trusted': False,
            'premium': False,
            'accept_handicapped': False,
            'accept_kids': False,
            'response_letter_required': False,
            'published_at': None
        }
        
        # === ДАТА ПУБЛИКАЦИИ (ВАЖНО!) ===
        published_at = None
        
        # 1. Сначала пробуем JSON-LD
        json_ld = extract_json_ld(soup)
        if json_ld and 'datePosted' in json_ld:
            try:
                published_at = date_parser.parse(json_ld['datePosted'])
                logger.debug(f"Got date from JSON-LD: {published_at}")
            except Exception as e:
                logger.debug(f"Failed to parse JSON-LD date: {e}")
        
        # 2. Парсим из HTML
        if not published_at:
            date_selectors = [
                'p[data-qa="vacancy-creation-time-redesigned"]',
                'p[data-qa="vacancy-creation-time"]',
                'p[data-qa="vacancy-view-creation-date"]',
                'span.vacancy-creation-time-redesigned',
                'span.vacancy-creation-time',
                'span[data-qa="vacancy-serp__vacancy-date"]'
            ]
            
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    published_at = parse_russian_date(date_text)
                    if published_at:
                        logger.debug(f"Parsed date from HTML: {published_at}")
                        break
        
        # 3. Из meta тегов
        if not published_at:
            meta_date = soup.find('meta', {'property': 'article:published_time'})
            if meta_date and meta_date.get('content'):
                try:
                    published_at = date_parser.parse(meta_date['content'])
                    logger.debug(f"Got date from meta tag: {published_at}")
                except:
                    pass
        
        # 4. Fallback на текущую дату
        if not published_at:
            published_at = datetime.now()
            logger.debug(f"Using current date as fallback")
        
        result['published_at'] = published_at
        
        # === РАБОТОДАТЕЛЬ ===
        employer_selectors = [
            'a[data-qa="vacancy-company-name"]',
            'span[data-qa="vacancy-company-name"]'
        ]
        
        for selector in employer_selectors:
            employer_elem = soup.select_one(selector)
            if employer_elem:
                result['employer_name'] = employer_elem.get_text(strip=True)
                if employer_elem.name == 'a':
                    result['employer_url'] = urljoin(RABOTA_BASE_URL, employer_elem.get('href', ''))
                break
        
        if soup.find(class_=re.compile(r'vacancy-company-trusted|verified')):
            result['employer_trusted'] = True
        
        # === ОПИСАНИЕ ===
        desc_selectors = [
            'div[data-qa="vacancy-description"]',
            'div.vacancy-description',
            'div.g-user-content'
        ]
        
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                result['description_html'] = str(desc_elem)
                result['description_text'] = desc_elem.get_text(separator='\n', strip=True)
                break
        
        # === КЛЮЧЕВЫЕ НАВЫКИ ===
        result['key_skills'] = extract_key_skills_from_page(html_content)
        
        # === ЗАРПЛАТА ===
        salary_elem = soup.select_one('span[data-qa="vacancy-salary"]') or \
                     soup.select_one('div[data-qa="vacancy-salary"]')
        if salary_elem:
            result['salary'] = parse_salary(salary_elem)
        
        # === ОПЫТ ===
        exp_elem = soup.select_one('span[data-qa="vacancy-experience"]') or \
                  soup.select_one('p[data-qa="vacancy-experience"]')
        if exp_elem:
            exp_text = exp_elem.get_text(strip=True).lower()
            if 'не требуется' in exp_text or 'без опыта' in exp_text:
                result['experience_id'] = 'noExperience'
                result['experience_name'] = 'Нет опыта'
            elif any(x in exp_text for x in ['1 год', '1-3', 'от 1', '1–3']):
                result['experience_id'] = 'between1And3'
                result['experience_name'] = 'От 1 года до 3 лет'
            elif any(x in exp_text for x in ['3 года', '3-6', 'от 3', '3–6']):
                result['experience_id'] = 'between3And6'
                result['experience_name'] = 'От 3 до 6 лет'
            elif any(x in exp_text for x in ['более 6', 'от 6', '6 лет']):
                result['experience_id'] = 'moreThan6'
                result['experience_name'] = 'Более 6 лет'
        
        # === ТИП ЗАНЯТОСТИ ===
        emp_elem = soup.select_one('p[data-qa="vacancy-employment"]') or \
                  soup.select_one('span[data-qa="vacancy-employment"]')
        if emp_elem:
            emp_text = emp_elem.get_text(strip=True).lower()
            if 'частичная' in emp_text:
                result['employment_id'] = 'part'
                result['employment_name'] = 'Частичная занятость'
            elif 'проект' in emp_text:
                result['employment_id'] = 'project'
                result['employment_name'] = 'Проектная работа'
            elif 'стажировка' in emp_text:
                result['employment_id'] = 'probation'
                result['employment_name'] = 'Стажировка'
        
        # === ГРАФИК ===
        schedule_elem = soup.select_one('p[data-qa="vacancy-schedule"]') or \
                       soup.select_one('span[data-qa="vacancy-schedule"]')
        if schedule_elem:
            schedule_text = schedule_elem.get_text(strip=True).lower()
            if 'удален' in schedule_text or 'remote' in schedule_text:
                result['schedule_id'] = 'remote'
                result['schedule_name'] = 'Удалённая работа'
            elif 'гибк' in schedule_text:
                result['schedule_id'] = 'flexible'
                result['schedule_name'] = 'Гибкий график'
            elif 'смен' in schedule_text:
                result['schedule_id'] = 'shift'
                result['schedule_name'] = 'Сменный график'
        
        # === АДРЕС ===
        address_elem = soup.select_one('span[data-qa="vacancy-view-raw-address"]') or \
                      soup.select_one('div[data-qa="vacancy-address"]')
        if address_elem:
            address_text = address_elem.get_text(strip=True)
            result['address_raw'] = address_text
            parsed_address = parse_complex_address(address_text)
            result['address_city'] = parsed_address['city']
            result['address_street'] = parsed_address['street']
            result['address_building'] = parsed_address['building']
            result['metro_stations'] = parsed_address['metro_stations']
        
        # === КООРДИНАТЫ ===
        lat, lng = extract_coordinates(soup)
        if lat and lng:
            result['coordinates']['lat'] = lat
            result['coordinates']['lng'] = lng
        
        return result
        
    except Exception as e:
        logger.error(f"Error parsing vacancy page {vacancy_url}: {str(e)}")
        return None


def fetch_dictionaries(**context):
    """Загрузка справочников"""
    logger.info("Starting dictionaries fetch")
    
    pg_hook = PostgresHook(postgres_conn_id='vacancy_postgres')
    stats = {'areas': 0}
    
    try:
        belarus_regions = [
            {"id": "16", "name": "Беларусь", "parent_id": None},
            {"id": "1002", "name": "Минск", "parent_id": "16"},
            {"id": "1003", "name": "Брестская область", "parent_id": "16"},
            {"id": "1004", "name": "Витебская область", "parent_id": "16"},
            {"id": "1005", "name": "Гомельская область", "parent_id": "16"},
            {"id": "1006", "name": "Гродненская область", "parent_id": "16"},
            {"id": "1007", "name": "Минская область", "parent_id": "16"},
            {"id": "1008", "name": "Могилевская область", "parent_id": "16"},
        ]
        
        for region in belarus_regions:
            pg_hook.run(
                """
                INSERT INTO vacancies.areas (id, name, parent_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE 
                SET name = EXCLUDED.name, parent_id = EXCLUDED.parent_id
                """,
                parameters=(region['id'], region['name'], region['parent_id'])
            )
            stats['areas'] += 1
        
        logger.info(f"Loaded {stats['areas']} areas")
        
        context['ti'].xcom_push(key='dict_stats', value=stats)
        return stats
        
    except Exception as e:
        logger.error(f"Error in fetch_dictionaries: {str(e)}")
        raise


def fetch_new_vacancies(**context):
    """Загрузка новых вакансий с rabota.by с улучшенной обработкой"""
    logger.info("Starting new vacancies fetch from rabota.by")
    
    pg_hook = PostgresHook(postgres_conn_id='vacancy_postgres')
    session = get_rabota_session()
    
    # Параметры - увеличиваем лимиты
    search_text = Variable.get('rabota_search_text', default_var='программист')
    search_area = Variable.get('rabota_search_area', default_var='16')  # Исправлена опечатка
    max_vacancies = int(Variable.get('rabota_max_vacancies', default_var='200'))  # Увеличено
    max_pages = int(Variable.get('rabota_max_pages', default_var='10'))  # Увеличено
    
    total_processed = 0
    new_vacancies = 0
    updated_vacancies = 0
    skipped_existing = 0
    failed_saves = 0
    
    try:
        # Получаем все существующие ID без фильтра по дате
        existing_vacancies = set()
        result = pg_hook.get_records("SELECT id FROM vacancies.vacancies")
        if result:
            existing_vacancies = {row[0] for row in result}
            logger.info(f"Found {len(existing_vacancies)} existing vacancies in DB")
        
        page = 0
        vacancies_per_page = 20
        consecutive_empty_pages = 0
        
        while page < max_pages and new_vacancies < max_vacancies:
            search_params = {
                'text': search_text,
                'area': search_area,
                'page': page,
                'per_page': vacancies_per_page
            }
            
            logger.info(f"Fetching page {page + 1} of {max_pages}")
            
            response = session.get(RABOTA_SEARCH_URL, params=search_params, timeout=30)
            if response.status_code != 200:
                logger.warning(f"Got status {response.status_code}")
                break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Проверяем есть ли сообщение "ничего не найдено"
            no_items = soup.find('div', class_='vacancy-search-no-items')
            if no_items:
                logger.info("No more vacancies found - reached end of results")
                break
            
            # Ищем блоки вакансий различными способами
            vacancy_blocks = []
            
            # Селекторы для блоков вакансий
            block_selectors = [
                'div[data-qa="vacancy-serp__vacancy"]',
                'div.vacancy-serp-item',
                'div[class*="vacancy-serp-item"]',
                'article.vacancy-serp-item',
                'div.serp-item'
            ]
            
            for selector in block_selectors:
                blocks = soup.select(selector)
                if blocks:
                    vacancy_blocks = blocks
                    logger.info(f"Found {len(blocks)} vacancy blocks with selector: {selector}")
                    break
            
            # Если блоки не найдены, ищем прямые ссылки
            if not vacancy_blocks:
                vacancy_links = soup.find_all('a', href=re.compile(r'/vacancy/\d+'))
                if vacancy_links:
                    logger.info(f"Found {len(vacancy_links)} direct vacancy links")
                    # Создаём псевдо-блоки из ссылок
                    vacancy_blocks = [{'link': link} for link in vacancy_links]
                else:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 2:
                        logger.info("Two consecutive empty pages, stopping")
                        break
                    page += 1
                    continue
            else:
                consecutive_empty_pages = 0
            
            # Обрабатываем найденные вакансии
            for block in vacancy_blocks:
                if new_vacancies >= max_vacancies:
                    break
                
                try:
                    # Извлекаем ссылку
                    if isinstance(block, dict) and 'link' in block:
                        link_elem = block['link']
                    else:
                        link_elem = block.select_one('a[data-qa*="vacancy-title"]') or \
                                   block.select_one('a[href*="/vacancy/"]')
                    
                    if not link_elem:
                        continue
                    
                    href = link_elem.get('href', '')
                    vacancy_id_match = re.search(r'/vacancy/(\d+)', href)
                    
                    if not vacancy_id_match:
                        continue
                    
                    vacancy_id = int(vacancy_id_match.group(1))
                    
                    # Проверяем, обрабатывали ли уже
                    if vacancy_id in existing_vacancies:
                        skipped_existing += 1
                        logger.debug(f"Vacancy {vacancy_id} already exists")
                        continue
                    
                    total_processed += 1
                    
                    # Парсим вакансию
                    vacancy_url = urljoin(RABOTA_BASE_URL, href)
                    
                    # Проверяем что это rabota.by
                    if 'rabota.by' not in vacancy_url:
                        logger.debug(f"Skipping non-rabota.by URL: {vacancy_url}")
                        continue
                    
                    logger.info(f"Parsing vacancy {vacancy_id}")
                    
                    vacancy_data = parse_vacancy_page(session, vacancy_url)
                    if not vacancy_data:
                        logger.warning(f"Failed to parse vacancy {vacancy_id}")
                        failed_saves += 1
                        continue
                    
                    vacancy_name = link_elem.get_text(strip=True) or "Без названия"
                    
                    # === РАБОТОДАТЕЛЬ ===
                    employer_id = None
                    if vacancy_data.get('employer_name'):
                        employer = pg_hook.get_first(
                            "SELECT id FROM vacancies.employers WHERE name = %s",
                            parameters=(vacancy_data['employer_name'][:255],)  # Ограничение длины
                        )
                        
                        if employer:
                            employer_id = employer[0]
                        else:
                            # Создаём нового работодателя
                            try:
                                result = pg_hook.get_first(
                                    """
                                    INSERT INTO vacancies.employers (name, url, trusted)
                                    VALUES (%s, %s, %s)
                                    RETURNING id
                                    """,
                                    parameters=(
                                        vacancy_data['employer_name'][:255],
                                        (vacancy_data.get('employer_url') or '')[:500],
                                        vacancy_data.get('employer_trusted', False)
                                    )
                                )
                                if result:
                                    employer_id = result[0]
                                    logger.debug(f"Created employer: {vacancy_data['employer_name']} (ID: {employer_id})")
                            except Exception as e:
                                logger.error(f"Failed to create employer: {e}")
                    
                    # === ОПРЕДЕЛЯЕМ AREA_ID ===
                    area_id = search_area
                    if vacancy_data.get('address_city'):
                        city_map = {
                            'Минск': '1002',
                            'Брест': '1003', 
                            'Витебск': '1004',
                            'Гомель': '1005',
                            'Гродно': '1006',
                            'Могилев': '1008'
                        }
                        area_id = city_map.get(vacancy_data['address_city'], search_area)
                    
                    # === ПРОВЕРЯЕМ И ФОРМАТИРУЕМ ДАТУ ===
                    published_at = vacancy_data.get('published_at')
                    if not isinstance(published_at, datetime):
                        published_at = datetime.now()
                    
                    # === СОХРАНЯЕМ ВАКАНСИЮ ===
                    try:
                        result = pg_hook.run(
                            """
                            INSERT INTO vacancies.vacancies (
                                id, name, url, employer_id, area_id,
                                description_html, description_text,
                                salary_from, salary_to, salary_currency, 
                                salary_gross, salary_description,
                                experience_id, experience_name,
                                employment_id, employment_name,
                                schedule_id, schedule_name,
                                address_raw, address_city, address_street, address_building,
                                address_lat, address_lng,
                                premium, accept_handicapped, accept_kids, response_letter_required,
                                published_at, created_at, archived
                            )
                            VALUES (
                                %s, %s, %s, %s, %s,
                                %s, %s,
                                %s, %s, %s,
                                %s, %s,
                                %s, %s,
                                %s, %s,
                                %s, %s,
                                %s, %s, %s, %s,
                                %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s
                            )
                            ON CONFLICT (id) DO UPDATE SET
                                name = EXCLUDED.name,
                                description_text = EXCLUDED.description_text,
                                description_html = EXCLUDED.description_html,
                                salary_from = EXCLUDED.salary_from,
                                salary_to = EXCLUDED.salary_to,
                                published_at = EXCLUDED.published_at,
                                updated_at = CURRENT_TIMESTAMP
                            RETURNING id
                            """,
                            parameters=(
                                vacancy_id,
                                vacancy_name[:500],  # Ограничения длины
                                vacancy_url[:500],
                                employer_id,
                                area_id,
                                (vacancy_data.get('description_html') or '')[:50000],
                                (vacancy_data.get('description_text') or '')[:50000],
                                vacancy_data['salary']['from'] if vacancy_data.get('salary') else None,
                                vacancy_data['salary']['to'] if vacancy_data.get('salary') else None,
                                vacancy_data['salary']['currency'] if vacancy_data.get('salary') else None,
                                vacancy_data['salary']['gross'] if vacancy_data.get('salary') else None,
                                (vacancy_data['salary']['description'] if vacancy_data.get('salary') else '')[:255],
                                vacancy_data.get('experience_id', 'noExperience'),
                                vacancy_data.get('experience_name', 'Нет опыта')[:100],
                                vacancy_data.get('employment_id', 'full'),
                                vacancy_data.get('employment_name', 'Полная занятость')[:100],
                                vacancy_data.get('schedule_id'),
                                (vacancy_data.get('schedule_name') or '')[:100],
                                (vacancy_data.get('address_raw') or '')[:500],
                                (vacancy_data.get('address_city') or '')[:100],
                                (vacancy_data.get('address_street') or '')[:200],
                                (vacancy_data.get('address_building') or '')[:50],
                                vacancy_data['coordinates']['lat'] if vacancy_data.get('coordinates') else None,
                                vacancy_data['coordinates']['lng'] if vacancy_data.get('coordinates') else None,
                                vacancy_data.get('premium', False),
                                vacancy_data.get('accept_handicapped', False),
                                vacancy_data.get('accept_kids', False),
                                vacancy_data.get('response_letter_required', False),
                                published_at,
                                datetime.now(),
                                False
                            )
                        )
                        
                        if result:
                            # Проверяем, новая это вакансия или обновление
                            if vacancy_id in existing_vacancies:
                                updated_vacancies += 1
                                logger.info(f"✅ Updated vacancy {vacancy_id}: {vacancy_name}")
                            else:
                                new_vacancies += 1
                                existing_vacancies.add(vacancy_id)
                                logger.info(f"✅ Added new vacancy {vacancy_id}: {vacancy_name}")
                    
                    except Exception as e:
                        logger.error(f"❌ Failed to save vacancy {vacancy_id}: {str(e)}")
                        failed_saves += 1
                        continue
                    
                    # === СОХРАНЯЕМ НАВЫКИ ===
                    if vacancy_data.get('key_skills'):
                        for skill_name in vacancy_data['key_skills']:
                            if skill_name:
                                try:
                                    skill_id = pg_hook.get_first(
                                        "SELECT vacancies.add_or_get_skill(%s)",
                                        parameters=(skill_name[:100],)
                                    )
                                    
                                    if skill_id:
                                        pg_hook.run(
                                            """
                                            INSERT INTO vacancies.vacancy_skills (vacancy_id, skill_id)
                                            VALUES (%s, %s)
                                            ON CONFLICT DO NOTHING
                                            """,
                                            parameters=(vacancy_id, skill_id[0])
                                        )
                                except Exception as e:
                                    logger.debug(f"Failed to add skill {skill_name}: {e}")
                    
                    # === СОХРАНЯЕМ СТАНЦИИ МЕТРО ===
                    if vacancy_data.get('metro_stations'):
                        for station_name in vacancy_data['metro_stations']:
                            try:
                                metro_id = pg_hook.get_first(
                                    "SELECT vacancies.add_or_get_metro(%s, %s)",
                                    parameters=(
                                        station_name[:100], 
                                        vacancy_data.get('address_city', 'Минск')[:100]
                                    )
                                )
                                
                                if metro_id:
                                    pg_hook.run(
                                        """
                                        INSERT INTO vacancies.vacancy_metro (vacancy_id, metro_id)
                                        VALUES (%s, %s)
                                        ON CONFLICT DO NOTHING
                                        """,
                                        parameters=(vacancy_id, metro_id[0])
                                    )
                            except Exception as e:
                                logger.debug(f"Failed to add metro station {station_name}: {e}")
                    
                    time.sleep(0.3)  # Небольшая пауза между запросами
                
                except Exception as e:
                    logger.error(f"Unexpected error processing vacancy: {str(e)}")
                    failed_saves += 1
                    continue
            
            page += 1
            logger.info(f"Page {page} completed: {new_vacancies} new, {updated_vacancies} updated")
            time.sleep(0.5)  # Пауза между страницами
        
        # === СОХРАНЯЕМ СТАТИСТИКУ ===
        try:
            pg_hook.run(
                """
                INSERT INTO vacancies.parse_statistics 
                (source, total_processed, new_vacancies, updated_vacancies, failed_vacancies)
                VALUES (%s, %s, %s, %s, %s)
                """,
                parameters=(
                    'rabota.by', 
                    total_processed, 
                    new_vacancies, 
                    updated_vacancies, 
                    failed_saves
                )
            )
        except Exception as e:
            logger.error(f"Failed to save statistics: {e}")
        
        logger.info(f"""
        ✅ Parsing completed:
        - Total processed: {total_processed}
        - New vacancies: {new_vacancies}
        - Updated vacancies: {updated_vacancies}
        - Skipped existing: {skipped_existing}
        - Failed to save: {failed_saves}
        """)
        
        context['ti'].xcom_push(key='new_vacancies', value=new_vacancies)
        context['ti'].xcom_push(key='updated_vacancies', value=updated_vacancies)
        context['ti'].xcom_push(key='total_processed', value=total_processed)
        
        return {
            'new': new_vacancies, 
            'updated': updated_vacancies,
            'skipped': skipped_existing, 
            'failed': failed_saves,
            'total': total_processed
        }
        
    except Exception as e:
        logger.error(f"Critical error in fetch_new_vacancies: {str(e)}")
        raise


# Создание DAG
dag = DAG(
    'rabota_fetch_new_vacancies',
    default_args=default_args,
    description='Загрузка новых вакансий с rabota.by с полным парсингом',
    schedule_interval=timedelta(hours=6),
    catchup=False,
    tags=['rabota', 'vacancies', 'etl', 'full']
)

# Задачи
fetch_dictionaries_task = PythonOperator(
    task_id='fetch_dictionaries',
    python_callable=fetch_dictionaries,
    dag=dag
)

fetch_new_vacancies_task = PythonOperator(
    task_id='fetch_new_vacancies',
    python_callable=fetch_new_vacancies,
    dag=dag
)

# Зависимости
fetch_dictionaries_task >> fetch_new_vacancies_task