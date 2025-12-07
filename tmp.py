import requests
import logging
import time
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import psycopg2

RABOTA_BASE_URL = "https://rabota.by"
RABOTA_SEARCH_URL = f"{RABOTA_BASE_URL}/search/vacancy"
RABOTA_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

logger = logging.getLogger(__name__)

connection = psycopg2.connect(
    host="localhost",
    port=5432,
    database="hh_data",
    user="kiselevas",
    password="qwerty"
)


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
        
        # Извлекаем JSON-LD структурированные данные, если есть
        json_ld = soup.find('script', type='application/ld+json')
        vacancy_data = {}
        
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, list):
                    data = data[0] if data else {}
                vacancy_data = data
            except:
                pass
        
        # Парсим основные блоки
        result = {
            'description': '',
            'tasks': '',
            'requirements': '',
            'advantages': '',
            'offers': '',
            'skills': []
        }
        
        # Ищем блоки с описанием используя правильный селектор
        description_block = soup.select_one("div.g-user-content")
        if description_block:
            result['description'] = description_block.get_text(separator='\n', strip=True)
        
        # Ищем блок "Задачи"
        tasks_block = soup.find(text=re.compile(r'Задачи|Обязанности', re.I))
        if tasks_block:
            parent = tasks_block.find_parent()
            if parent:
                result['tasks'] = parent.get_text(strip=True)
        
        # Ищем блок "Мы ожидаем"
        requirements_block = soup.find(text=re.compile(r'Мы ожидаем|Требования', re.I))
        if requirements_block:
            parent = requirements_block.find_parent()
            if parent:
                result['requirements'] = parent.get_text(strip=True)
        
        # Ищем блок "Будет плюсом"
        advantages_block = soup.find(text=re.compile(r'Будет плюсом|Преимущества', re.I))
        if advantages_block:
            parent = advantages_block.find_parent()
            if parent:
                result['advantages'] = parent.get_text(strip=True)
        
        # Ищем блок "Мы предлагаем"
        offers_block = soup.find(text=re.compile(r'Мы предлагаем|Условия', re.I))
        if offers_block:
            parent = offers_block.find_parent()
            if parent:
                result['offers'] = parent.get_text(strip=True)
        
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

def fetch_new_vacancies():
    session = get_rabota_session()

    search_text = 'Programmer'
    search_area = '16'
    date_threshold = datetime.now() - timedelta(days=14)

    total_processed = 0
    new_vacancies = 0
    updated_vacancies = 0

    try:
        search_params = {
            'text': search_text,
            'area': search_area,
            'page': 0
        }

        logger.info(f"Fetching vacancies (filtering by published_at >= {date_threshold.strftime('%Y-%m-%d')})")
        logger.info(f"Search params: {search_params}")

        page = 0
        max_pages = 10

        while page < max_pages:
            search_params['page'] = page
            logger.info(f"Fetching page {page + 1}")

            try:
                response = session.get(RABOTA_SEARCH_URL, params=search_params, timeout=30)

                if response.status_code != 200:
                    logger.warning(f"Got status {response.status_code}, trying alternative method")
                    break

                html_content = response.text
                json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', html_content, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                        vacancies_data = data.get('vacancies', {}).get('items', [])
                    except:
                        vacancies_data = []
                else:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    vacancy_blocks = soup.select("div.vacancy-info--ieHKDTkezpEj0Gsx")
                    vacancies_data = []

                    for vacancy_block in vacancy_blocks:
                        try:
                            title_elem = vacancy_block.select_one("span[data-qa='serp-item__title-text']")
                            vacancy_link_elem = vacancy_block.select_one("a[data-qa='serp-item__title']")

                            if not vacancy_link_elem or not vacancy_link_elem.get('href'):
                                continue

                            href = vacancy_link_elem.get('href', '')
                            vacancy_id_match = re.search(r'/vacancy/(\d+)', href)
                            if not vacancy_id_match:
                                continue

                            vacancy_id = int(vacancy_id_match.group(1))

                            if href.startswith('http://') or href.startswith('https://'):
                                url = href
                            elif href.startswith('/'):
                                url = RABOTA_BASE_URL + href
                            else:
                                url = f"{RABOTA_BASE_URL}/{href}"

                            name = title_elem.get_text(strip=True) if title_elem else ''

                            experience_id = 'noExperience'
                            experience_name = 'Нет опыта'

                            experience_selectors = [
                                "span[data-qa='vacancy-serp__vacancy-work-experience-noExperience']",
                                "span[data-qa='vacancy-serp__vacancy-work-experience-between1And3']",
                                "span[data-qa='vacancy-serp__vacancy-work-experience-between3And6']",
                                "span[data-qa='vacancy-serp__vacancy-work-experience-moreThan6']",
                                "span[data-qa*='vacancy-work-experience']"
                            ]

                            for selector in experience_selectors:
                                exp_elem = vacancy_block.select_one(selector)
                                if exp_elem:
                                    exp_text = exp_elem.get_text(strip=True).lower()
                                    if 'не требуется' in exp_text or 'без опыта' in exp_text or 'нет опыта' in exp_text:
                                        experience_id = 'noExperience'
                                        experience_name = 'Нет опыта'
                                    elif '1' in exp_text and '3' in exp_text:
                                        experience_id = 'between1And3'
                                        experience_name = 'От 1 года до 3 лет'
                                    elif '3' in exp_text and '6' in exp_text:
                                        experience_id = 'between3And6'
                                        experience_name = 'От 3 до 6 лет'
                                    elif 'более' in exp_text or '6' in exp_text:
                                        experience_id = 'moreThan6'
                                        experience_name = 'Более 6 лет'
                                    break

                            vacancies_data.append({
                                'id': vacancy_id,
                                'url': url,
                                'name': name,
                                'experience_id': experience_id,
                                'experience_name': experience_name
                            })
                        except Exception as e:
                            logger.debug(f"Error parsing vacancy card: {str(e)}")
                            continue

                if not vacancies_data:
                    logger.info("No more vacancies found, stopping")
                    break

                for vacancy_item in vacancies_data:
                    try:
                        vacancy_id = vacancy_item.get('id')
                        if not vacancy_id:
                            continue

                        cursor = connection.cursor()
                        cursor.execute("SELECT id FROM vacancies.vacancies WHERE id = %s", (vacancy_id,))
                        exists = cursor.fetchone() is not None
                        cursor.close()

                        if exists:
                            logger.debug(f"Vacancy {vacancy_id} already exists, skipping")
                            continue

                        vacancy_url = vacancy_item.get('url') or f"{RABOTA_BASE_URL}/vacancy/{vacancy_id}"

                        if vacancy_url.startswith('http://') or vacancy_url.startswith('https://'):
                            if 'rabota.byhttps://' in vacancy_url or 'rabota.byhttp://' in vacancy_url:
                                vacancy_url = vacancy_url.replace('rabota.byhttps://', 'https://')
                                vacancy_url = vacancy_url.replace('rabota.byhttp://', 'http://')
                        elif vacancy_url.startswith('/'):
                            vacancy_url = RABOTA_BASE_URL + vacancy_url
                        else:
                            vacancy_url = f"{RABOTA_BASE_URL}/{vacancy_url}"
                        
                        vacancy_url = vacancy_url[:vacancy_url.find('?')]
                        logger.debug(f"Parsing vacancy {vacancy_id} from URL: {vacancy_url}")
                        vacancy_details = parse_vacancy_page(session, vacancy_url)

                        if not vacancy_details:
                            logger.warning(f"Could not parse vacancy {vacancy_id}")
                            continue

                        experience_id = vacancy_item.get('experience_id') or vacancy_details.get('experience_id', 'noExperience')
                        experience_name = vacancy_item.get('experience_name') or vacancy_details.get('experience_name', 'Нет опыта')

                        cursor = connection.cursor()
                        cursor.execute(
                            """
                            INSERT INTO vacancies.vacancies (
                                id, name, employer_id, area_id, description,
                                tasks, requirements, advantages, offers,
                                experience_id, experience_name,
                                published_at, created_at, url, archived
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE
                            SET name = EXCLUDED.name,
                                description = EXCLUDED.description,
                                tasks = EXCLUDED.tasks,
                                requirements = EXCLUDED.requirements,
                                advantages = EXCLUDED.advantages,
                                offers = EXCLUDED.offers,
                                experience_id = EXCLUDED.experience_id,
                                experience_name = EXCLUDED.experience_name,
                                updated_at = CURRENT_TIMESTAMP
                            """,
                            (
                                vacancy_id,
                                vacancy_item.get('name', ''),
                                1,
                                search_area,
                                vacancy_details.get('description', ''),
                                vacancy_details.get('tasks', ''),
                                vacancy_details.get('requirements', ''),
                                vacancy_details.get('advantages', ''),
                                vacancy_details.get('offers', ''),
                                experience_id,
                                experience_name,
                                datetime.now(),
                                datetime.now(),
                                vacancy_url,
                                False
                            )
                        )

                        for skill in vacancy_details.get('skills', []):
                            if skill:
                                cursor.execute(
                                    """
                                    INSERT INTO vacancies.vacancy_skills (vacancy_id, skill_name)
                                    VALUES (%s, %s)
                                    ON CONFLICT (vacancy_id, skill_name) DO NOTHING
                                    """,
                                    (vacancy_id, skill)
                                )

                        connection.commit()
                        cursor.close()

                        new_vacancies += 1
                        total_processed += 1

                        time.sleep(0.5)

                    except Exception as e:
                        logger.error(f"Error processing vacancy {vacancy_item.get('id')}: {str(e)}")
                        continue

                page += 1
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error fetching page {page}: {str(e)}")
                break

        logger.info(f"Processed %s vacancies, %s new, %s updated",
                    total_processed, new_vacancies, updated_vacancies)

        return new_vacancies

    except Exception as e:
        logger.error(f"Error fetching vacancies: {str(e)}")
        raise


fetch_new_vacancies()
