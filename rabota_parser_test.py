"""
Улучшенный парсер вакансий с rabota.by (без Selenium)
Извлекает полную информацию о вакансиях включая все поля для фильтров,
поиска, сортировки и отображения на карте
"""

import json
import re
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Константы
RABOTA_BASE_URL = "https://rabota.by"
SEARCH_URL = f"{RABOTA_BASE_URL}/search/vacancy"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
MAX_VACANCIES = 10  # Максимум вакансий для парсинга

@dataclass
class Employer:
    """Информация о работодателе"""
    id: Optional[int] = None
    name: Optional[str] = None
    url: Optional[str] = None
    logo_url: Optional[str] = None
    trusted: bool = False
    description: Optional[str] = None
    website: Optional[str] = None
    
@dataclass
class Address:
    """Адрес вакансии"""
    city: Optional[str] = None
    street: Optional[str] = None
    building: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    metro_stations: List[str] = field(default_factory=list)
    raw: Optional[str] = None

@dataclass 
class Salary:
    """Информация о зарплате"""
    from_value: Optional[int] = None
    to_value: Optional[int] = None
    currency: Optional[str] = None
    gross: Optional[bool] = None
    description: Optional[str] = None

@dataclass
class Vacancy:
    """Полная модель вакансии"""
    id: int
    name: str
    url: str
    employer: Employer
    published_at: Optional[str] = None
    created_at: Optional[str] = None
    archived: bool = False
    premium: bool = False
    
    # Описание с форматированием (единое поле)
    description_html: Optional[str] = None
    description_text: Optional[str] = None
    
    # Ключевые навыки (отдельный блок на сайте)
    key_skills: List[str] = field(default_factory=list)
    
    # Условия работы
    salary: Optional[Salary] = None
    experience_id: Optional[str] = None
    experience_name: Optional[str] = None
    schedule_id: Optional[str] = None  
    schedule_name: Optional[str] = None
    employment_id: Optional[str] = None
    employment_name: Optional[str] = None
    
    # Для карты
    address: Optional[Address] = None
    working_days: List[str] = field(default_factory=list)
    working_time_intervals: List[str] = field(default_factory=list)
    working_time_modes: List[str] = field(default_factory=list)
    
    # Дополнительная информация
    accept_handicapped: bool = False
    accept_kids: bool = False
    specializations: List[Dict[str, str]] = field(default_factory=list)
    professional_roles: List[Dict[str, str]] = field(default_factory=list)
    languages: List[Dict[str, str]] = field(default_factory=list)
    driver_license_types: List[str] = field(default_factory=list)
    
    # Контакты
    contacts: Optional[Dict[str, Any]] = None
    response_letter_required: bool = False
    response_url: Optional[str] = None
    test: Optional[Dict[str, str]] = None
    
    # Метаданные
    alternate_url: Optional[str] = None
    apply_alternate_url: Optional[str] = None
    code: Optional[str] = None
    department: Optional[Dict[str, str]] = None
    area: Optional[Dict[str, str]] = None

class RabotaByParser:
    """Парсер вакансий с сайта rabota.by"""
    
    def __init__(self):
        self.session = self._create_session()
            
    def _create_session(self) -> requests.Session:
        """Создание HTTP сессии с правильными заголовками"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,be;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://rabota.by/',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
        return session
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict]:
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
    
    def _extract_initial_state(self, html: str) -> Optional[Dict]:
        """Извлечение __INITIAL_STATE__ из HTML"""
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', html, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None
    
    def _extract_vacancy_data(self, html: str) -> Optional[Dict]:
        """
        Извлечение данных вакансии из различных JSON структур на странице
        """
        # Ищем различные паттерны JSON данных
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'HH\.VacancyResponsePage\.init\(({.+?})\);',
            r'HH\.globalVacancyData\s*=\s*({.+?});',
            r'"vacancy":\s*({.+?}),\s*"',
            r'data-vacancy-json="([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    # Если это атрибут HTML, нужно декодировать
                    if 'data-vacancy-json' in pattern:
                        import html as html_lib
                        json_str = html_lib.unescape(match.group(1))
                    else:
                        json_str = match.group(1)
                    
                    data = json.loads(json_str)
                    return data
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.debug(f"Failed to parse JSON with pattern {pattern}: {e}")
                    continue
        
        return None
    
    def _parse_experience(self, text: str) -> tuple:
        """Парсинг опыта работы"""
        text_lower = text.lower() if text else ''
        
        if 'не требуется' in text_lower or 'без опыта' in text_lower or 'нет опыта' in text_lower:
            return 'noExperience', 'Нет опыта'
        elif any(x in text_lower for x in ['1 год', '1-3', 'от 1', 'от года', '1–3']):
            return 'between1And3', 'От 1 года до 3 лет'
        elif any(x in text_lower for x in ['3 года', '3-6', 'от 3', '3–6']):
            return 'between3And6', 'От 3 до 6 лет'
        elif any(x in text_lower for x in ['более 6', 'от 6', '6 лет', 'больше 6']):
            return 'moreThan6', 'Более 6 лет'
        
        return None, text
    
    def _parse_employment(self, text: str) -> tuple:
        """Парсинг типа занятости"""
        text_lower = text.lower() if text else ''
        
        if 'полная' in text_lower or 'full' in text_lower:
            return 'full', 'Полная занятость'
        elif 'частичная' in text_lower or 'part' in text_lower:
            return 'part', 'Частичная занятость'
        elif 'проект' in text_lower:
            return 'project', 'Проектная работа'
        elif 'стажировка' in text_lower or 'intern' in text_lower:
            return 'probation', 'Стажировка'
        
        return None, text
    
    def _parse_schedule(self, text: str) -> tuple:
        """Парсинг графика работы"""
        text_lower = text.lower() if text else ''
        
        if 'удален' in text_lower or 'remote' in text_lower:
            return 'remote', 'Удаленная работа'
        elif 'гибк' in text_lower or 'flexible' in text_lower:
            return 'flexible', 'Гибкий график'
        elif 'смен' in text_lower:
            return 'shift', 'Сменный график'
        elif 'вахт' in text_lower:
            return 'flyInFlyOut', 'Вахтовый метод'
        elif '5/2' in text_lower or 'пятидневка' in text_lower:
            return 'fullDay', 'Полный день'
        
        return None, text
    
    def _parse_salary(self, element) -> Optional[Salary]:
        """Парсинг информации о зарплате"""
        if not element:
            return None
            
        salary = Salary()
        text = element.get_text(strip=True) if hasattr(element, 'get_text') else str(element)
        
        # Извлечение чисел
        numbers = re.findall(r'(\d+(?:\s?\d{3})*)', text)
        numbers = [int(n.replace(' ', '').replace('\xa0', '')) for n in numbers if n]
        
        if numbers:
            if len(numbers) >= 2:
                salary.from_value = numbers[0]
                salary.to_value = numbers[1]
            elif 'от' in text.lower():
                salary.from_value = numbers[0]
            elif 'до' in text.lower():
                salary.to_value = numbers[0]
            else:
                salary.from_value = numbers[0]
                salary.to_value = numbers[0]
        
        # Валюта
        if 'USD' in text or '$' in text:
            salary.currency = 'USD'
        elif 'EUR' in text or '€' in text:
            salary.currency = 'EUR'
        elif 'BYN' in text or 'руб' in text.lower() or 'br' in text.lower():
            salary.currency = 'BYN'
        else:
            salary.currency = 'BYN'
        
        # Гросс/нет
        salary.gross = 'до вычета' in text.lower() or 'gross' in text.lower()
        salary.description = text
        
        return salary
    
    def _parse_complex_address(self, address_text: str) -> Dict[str, Any]:
        """
        Умный парсинг сложного адреса
        Пример: 'Минск,Молодежная,Площадь Франтишка Богушевича,Фрунзенская,Юбилейная площадь, улица Тимирязева, 9к10'
        Логика: город слева, здание и улица справа, всё между ними - метро
        """
        result = {
            'city': None,
            'street': None,
            'building': None,
            'metro_stations': []
        }
        
        if not address_text:
            return result
        
        # Разбиваем адрес на части
        parts = [p.strip() for p in re.split(r'[,;]', address_text) if p.strip()]
        
        if not parts:
            return result
        
        # 1. Первая часть - обычно город
        city_keywords = ['Минск', 'Брест', 'Витебск', 'Гомель', 'Гродно', 'Могилев', 'Бобруйск', 'Барановичи', 'Пинск']
        first_part = parts[0]
        if any(keyword in first_part for keyword in city_keywords):
            result['city'] = first_part
            parts = parts[1:]  # Убираем город из списка
        
        if not parts:
            return result
        
        # 2. Идём с конца и ищем здание и улицу
        # Последний элемент - проверяем на номер дома
        last_part = parts[-1] if parts else None
        if last_part:
            # Проверяем, содержит ли номер дома/корпуса
            if re.search(r'\d+[а-яa-z]?\d*|к\d+|корпус\s*\d+|стр\s*\d+|д\.\s*\d+', last_part, re.IGNORECASE):
                result['building'] = last_part
                parts = parts[:-1]  # Убираем здание
        
        # Предпоследний элемент (после удаления здания) - проверяем на улицу
        if parts:
            last_part = parts[-1]
            # Проверяем, является ли это улицей
            street_keywords = ['улица', 'ул.', 'проспект', 'пр.', 'пр-т', 'переулок', 'пер.', 
                             'площадь', 'пл.', 'бульвар', 'б-р', 'проезд', 'шоссе', 
                             'набережная', 'наб.', 'тракт']
            if any(keyword in last_part.lower() for keyword in street_keywords):
                result['street'] = last_part
                parts = parts[:-1]  # Убираем улицу
        
        # 3. Всё что осталось между городом и улицей/домом - станции метро
        for part in parts:
            # Очищаем от префиксов метро
            clean_station = re.sub(r'(?:^|\s)(?:м\.|метро|ст\.м\.|станция метро)\s*', '', part, flags=re.IGNORECASE)
            clean_station = clean_station.strip()
            
            if clean_station:
                # Добавляем как станцию метро
                result['metro_stations'].append(clean_station)
        
        return result
    
    def _extract_coordinates(self, soup: BeautifulSoup) -> tuple:
        """Извлечение координат из карты"""
        lat, lng = None, None
        
        # 1. В data-атрибутах
        map_container = soup.find(attrs={'data-latitude': True, 'data-longitude': True})
        if map_container:
            try:
                lat = float(map_container.get('data-latitude'))
                lng = float(map_container.get('data-longitude'))
            except (ValueError, TypeError):
                pass
        
        # 2. В JavaScript коде страницы
        if not lat:
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Различные паттерны координат
                    patterns = [
                        r'"latitude":\s*([\d.]+)',
                        r'"lat":\s*([\d.]+)',
                        r'latitude["\']?\s*[:=]\s*([\d.]+)',
                        r'lat["\']?\s*[:=]\s*([\d.]+)',
                    ]
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
        
        # 3. В iframe с картой
        if not lat:
            iframe = soup.find('iframe', src=re.compile(r'maps|yandex'))
            if iframe:
                src = iframe.get('src', '')
                # Yandex Maps
                coord_match = re.search(r'll=([\d.]+)%2C([\d.]+)', src)
                if not coord_match:
                    coord_match = re.search(r'll=([\d.]+),([\d.]+)', src)
                # Google Maps
                if not coord_match:
                    coord_match = re.search(r'!3d([\d.]+)!4d([\d.]+)', src)
                
                if coord_match:
                    try:
                        lat = float(coord_match.group(1))
                        lng = float(coord_match.group(2))
                    except ValueError:
                        pass
        
        # 4. В ссылке на карту
        if not lat:
            map_link = soup.find('a', href=re.compile(r'maps|yandex\.by/maps'))
            if map_link:
                href = map_link.get('href', '')
                coord_match = re.search(r'll=([\d.]+),([\d.]+)', href)
                if not coord_match:
                    coord_match = re.search(r'@([\d.]+),([\d.]+)', href)
                
                if coord_match:
                    try:
                        lat = float(coord_match.group(1))
                        lng = float(coord_match.group(2))
                    except ValueError:
                        pass
        
        return lat, lng
    
    def _extract_key_skills_from_page_data(self, html: str) -> List[str]:
        """
        Извлечение ключевых навыков из данных страницы
        Ищем в JSON структурах на странице
        """
        key_skills = []
        
        # Ищем keySkills в различных JSON структурах
        patterns = [
            r'"keySkills":\s*{[^}]*"keySkill":\s*\[([^\]]+)\]',
            r'"keySkill":\s*\[([^\]]+)\]',
            r'"key_skills":\s*\[([^\]]+)\]',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    # Извлекаем строку со списком навыков
                    skills_str = match.group(1)
                    # Парсим навыки из строки
                    skills = re.findall(r'"([^"]+)"', skills_str)
                    key_skills.extend(skills)
                    if key_skills:
                        logger.info(f"Found {len(key_skills)} key skills from page data")
                        return key_skills
                except Exception as e:
                    logger.debug(f"Error extracting skills from pattern {pattern}: {e}")
        
        # Альтернативный метод - ищем весь JSON объект
        vacancy_data = self._extract_vacancy_data(html)
        if vacancy_data:
            # Различные пути к навыкам в JSON
            paths = [
                ['keySkills', 'keySkill'],
                ['key_skills'],
                ['skills'],
                ['vacancy', 'keySkills', 'keySkill'],
                ['vacancy', 'key_skills'],
            ]
            
            for path in paths:
                try:
                    current = vacancy_data
                    for key in path:
                        if isinstance(current, dict) and key in current:
                            current = current[key]
                        else:
                            break
                    else:
                        # Успешно прошли весь путь
                        if isinstance(current, list):
                            key_skills = [str(s) for s in current]
                            if key_skills:
                                logger.info(f"Found {len(key_skills)} key skills from JSON path {' > '.join(path)}")
                                return key_skills
                except Exception as e:
                    logger.debug(f"Error extracting skills from path {path}: {e}")
        
        return key_skills
    
    def parse_vacancy_list(self, search_text: str = "программист", 
                          area: str = "16", page: int = 0) -> List[Dict[str, Any]]:
        """Парсинг списка вакансий"""
        vacancies = []
        
        try:
            # Формируем параметры поиска
            params = {
                'text': search_text,
                'area': area,  # 16 - Беларусь
                'page': page
            }
            
            logger.info(f"Fetching search results: {SEARCH_URL}")
            logger.info(f"Parameters: {params}")
            
            response = self.session.get(SEARCH_URL, params=params, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Пробуем извлечь данные из __INITIAL_STATE__
            initial_state = self._extract_initial_state(response.text)
            if initial_state:
                logger.info("Found __INITIAL_STATE__ data")
                if 'vacancies' in initial_state and 'items' in initial_state['vacancies']:
                    vacancy_items = initial_state['vacancies']['items']
                    logger.info(f"Found {len(vacancy_items)} vacancies in initial state")
                    
                    for item in vacancy_items[:MAX_VACANCIES]:
                        try:
                            vacancy_url = f"{RABOTA_BASE_URL}/vacancy/{item['id']}"
                            logger.info(f"Parsing vacancy from initial state: {vacancy_url}")
                            detailed_info = self.parse_vacancy_page(vacancy_url, initial_data=item)
                            if detailed_info:
                                vacancies.append(detailed_info)
                            time.sleep(0.5)
                        except Exception as e:
                            logger.error(f"Error processing initial state vacancy: {e}")
                            continue
            
            # Если не нашли в initial state, парсим HTML
            if not vacancies:
                logger.info("Parsing HTML for vacancy blocks")
                
                # Используем различные селекторы
                selectors = [
                    'div[data-qa="vacancy-serp__vacancy"]',
                    'div.vacancy-serp-item',
                    'div[class*="vacancy-serp-item"]',
                    'div.serp-item',
                    'article[data-qa="vacancy-serp__vacancy"]'
                ]
                
                vacancy_blocks = []
                for selector in selectors:
                    blocks = soup.select(selector)
                    if blocks:
                        vacancy_blocks = blocks
                        logger.info(f"Found {len(blocks)} vacancy blocks using selector: {selector}")
                        break
                
                if not vacancy_blocks:
                    # Альтернативный подход - ищем по ссылкам
                    logger.info("Using alternative approach - searching for vacancy links")
                    vacancy_links = soup.find_all('a', href=re.compile(r'/vacancy/\d+'))
                    logger.info(f"Found {len(vacancy_links)} vacancy links")
                    
                    processed_ids = set()
                    for link in vacancy_links[:MAX_VACANCIES]:
                        href = link.get('href', '')
                        vacancy_id_match = re.search(r'/vacancy/(\d+)', href)
                        if vacancy_id_match:
                            vacancy_id = vacancy_id_match.group(1)
                            if vacancy_id not in processed_ids:
                                processed_ids.add(vacancy_id)
                                vacancy_url = urljoin(RABOTA_BASE_URL, href)
                                logger.info(f"Parsing vacancy: {vacancy_url}")
                                vacancy_data = self.parse_vacancy_page(vacancy_url)
                                if vacancy_data:
                                    vacancies.append(vacancy_data)
                                time.sleep(0.5)
                else:
                    # Обрабатываем найденные блоки
                    for block in vacancy_blocks[:MAX_VACANCIES]:
                        vacancy_info = self._extract_vacancy_info_from_block(block)
                        if vacancy_info and vacancy_info.get('url'):
                            logger.info(f"Parsing vacancy: {vacancy_info['url']}")
                            detailed_info = self.parse_vacancy_page(vacancy_info['url'])
                            if detailed_info:
                                vacancies.append(detailed_info)
                            time.sleep(0.5)
                    
        except Exception as e:
            logger.error(f"Error in parse_vacancy_list: {e}")
            import traceback
            traceback.print_exc()
        
        return vacancies
    
    def _extract_vacancy_info_from_block(self, block) -> Dict[str, Any]:
        """Извлечение базовой информации о вакансии из блока списка"""
        info = {}
        
        try:
            # Название и ссылка
            title_selectors = [
                'a[data-qa="vacancy-serp__vacancy-title"]',
                'a[data-qa="serp-item__title"]',
                'a.bloko-link',
                'a[href*="/vacancy/"]'
            ]
            
            title_elem = None
            for selector in title_selectors:
                title_elem = block.select_one(selector)
                if title_elem and title_elem.get('href'):
                    break
            
            if title_elem:
                info['name'] = title_elem.get_text(strip=True)
                href = title_elem.get('href', '')
                info['url'] = urljoin(RABOTA_BASE_URL, href)
                
                # ID из URL
                id_match = re.search(r'/vacancy/(\d+)', href)
                if id_match:
                    info['id'] = int(id_match.group(1))
                
        except Exception as e:
            logger.debug(f"Error extracting vacancy info from block: {e}")
        
        return info
    
    def parse_vacancy_page(self, url: str, initial_data: Dict = None) -> Optional[Dict[str, Any]]:
        """Парсинг страницы конкретной вакансии"""
        try:
            logger.info(f"Fetching vacancy page: {url}")
            
            # Извлекаем ID из URL
            id_match = re.search(r'/vacancy/(\d+)', url)
            if not id_match:
                logger.error(f"Cannot extract ID from URL: {url}")
                return None
            
            vacancy_id = int(id_match.group(1))
            
            # Получаем страницу
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Извлекаем JSON-LD данные
            json_ld = self._extract_json_ld(soup)
            
            # Создаем объекты
            employer = Employer()
            address = Address()
            salary = None
            
            # === НАЗВАНИЕ ВАКАНСИИ ===
            name = None
            title_selectors = [
                'h1[data-qa="vacancy-title"]',
                'h1.bloko-header-section-1',
                'h1[class*="vacancy-title"]'
            ]
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    name = title_elem.get_text(strip=True)
                    break
            
            if not name and json_ld:
                name = json_ld.get('title')
            
            if not name:
                name = "Без названия"
            
            # === РАБОТОДАТЕЛЬ ===
            employer_selectors = [
                'a[data-qa="vacancy-company-name"]',
                'span[data-qa="vacancy-company-name"]',
                'div.vacancy-company-name a',
                'span.vacancy-company-name'
            ]
            
            for selector in employer_selectors:
                employer_elem = soup.select_one(selector)
                if employer_elem:
                    employer.name = employer_elem.get_text(strip=True)
                    if employer_elem.name == 'a':
                        employer.url = urljoin(RABOTA_BASE_URL, employer_elem.get('href', ''))
                    break
            
            if not employer.name and json_ld and 'hiringOrganization' in json_ld:
                employer.name = json_ld['hiringOrganization'].get('name')
            
            # Логотип компании
            logo_elem = soup.find('img', class_=re.compile(r'vacancy-company-logo'))
            if logo_elem:
                employer.logo_url = logo_elem.get('src')
            
            # Проверенная компания
            if soup.find(class_=re.compile(r'vacancy-company-trusted|verified')):
                employer.trusted = True
            
            # === ОПИСАНИЕ ВАКАНСИИ (БЕЗ РАЗБИВКИ НА СЕКЦИИ) ===
            description_html = ""
            description_text = ""
            
            desc_selectors = [
                'div[data-qa="vacancy-description"]',
                'div.vacancy-description',
                'div.g-user-content',
                'div.b-vacancy-desc',
                'div.vacancy-section'
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    # Сохраняем HTML с форматированием
                    description_html = str(desc_elem)
                    # Текстовая версия
                    description_text = desc_elem.get_text(separator='\n', strip=True)
                    break
            
            if not description_text and json_ld and 'description' in json_ld:
                description_html = json_ld['description']
                soup_desc = BeautifulSoup(description_html, 'html.parser')
                description_text = soup_desc.get_text(separator='\n', strip=True)
            
            # === КЛЮЧЕВЫЕ НАВЫКИ ИЗ ДАННЫХ СТРАНИЦЫ ===
            key_skills = self._extract_key_skills_from_page_data(html_content)
            
            if not key_skills:
                logger.debug(f"No key skills found for vacancy {vacancy_id}")
            else:
                logger.info(f"✅ Found {len(key_skills)} key skills: {', '.join(key_skills)}")
            
            # === ЗАРПЛАТА ===
            salary_selectors = [
                'span[data-qa="vacancy-salary"]',
                'div[data-qa="vacancy-salary"]',
                'p.vacancy-salary',
                'span.vacancy-salary'
            ]
            
            for selector in salary_selectors:
                salary_elem = soup.select_one(selector)
                if salary_elem:
                    salary = self._parse_salary(salary_elem)
                    break
            
            # === ОПЫТ РАБОТЫ ===
            experience_id = 'noExperience'
            experience_name = 'Нет опыта'
            
            exp_selectors = [
                'span[data-qa="vacancy-experience"]',
                'p[data-qa="vacancy-experience"]',
                'div.vacancy-experience'
            ]
            
            for selector in exp_selectors:
                exp_elem = soup.select_one(selector)
                if exp_elem:
                    exp_text = exp_elem.get_text(strip=True)
                    parsed_exp = self._parse_experience(exp_text)
                    if parsed_exp[0]:
                        experience_id, experience_name = parsed_exp
                    break
            
            # === ТИП ЗАНЯТОСТИ ===
            employment_id = 'full'
            employment_name = 'Полная занятость'
            
            emp_selectors = [
                'p[data-qa="vacancy-employment"]',
                'span[data-qa="vacancy-employment"]'
            ]
            
            for selector in emp_selectors:
                emp_elem = soup.select_one(selector)
                if emp_elem:
                    emp_text = emp_elem.get_text(strip=True)
                    parsed_emp = self._parse_employment(emp_text)
                    if parsed_emp[0]:
                        employment_id, employment_name = parsed_emp
                    break
            
            if not employment_id and json_ld and 'employmentType' in json_ld:
                emp_type = json_ld['employmentType']
                if emp_type == 'FULL_TIME':
                    employment_id, employment_name = 'full', 'Полная занятость'
                elif emp_type == 'PART_TIME':
                    employment_id, employment_name = 'part', 'Частичная занятость'
            
            # === ГРАФИК РАБОТЫ ===
            schedule_id = None
            schedule_name = None
            
            schedule_selectors = [
                'p[data-qa="vacancy-schedule"]',
                'span[data-qa="vacancy-schedule"]'
            ]
            
            for selector in schedule_selectors:
                schedule_elem = soup.select_one(selector)
                if schedule_elem:
                    schedule_text = schedule_elem.get_text(strip=True)
                    parsed_schedule = self._parse_schedule(schedule_text)
                    if parsed_schedule[0]:
                        schedule_id, schedule_name = parsed_schedule
                    break
            
            # === АДРЕС И КООРДИНАТЫ ===
            address_raw = None
            address_selectors = [
                'span[data-qa="vacancy-view-raw-address"]',
                'div[data-qa="vacancy-address"]',
                'p[data-qa="vacancy-view-location"]',
                'span.vacancy-address-text'
            ]
            
            for selector in address_selectors:
                address_elem = soup.select_one(selector)
                if address_elem:
                    address_raw = address_elem.get_text(strip=True)
                    break
            
            if not address_raw and json_ld and 'jobLocation' in json_ld:
                location = json_ld['jobLocation']
                if 'address' in location:
                    addr = location['address']
                    if isinstance(addr, dict):
                        parts = []
                        if addr.get('addressLocality'):
                            parts.append(addr.get('addressLocality'))
                        if addr.get('streetAddress'):
                            parts.append(addr.get('streetAddress'))
                        address_raw = ', '.join(parts)
                    else:
                        address_raw = str(addr)
            
            # Умный парсинг адреса
            if address_raw:
                parsed_address = self._parse_complex_address(address_raw)
                address.city = parsed_address['city']
                address.street = parsed_address['street']
                address.building = parsed_address['building']
                address.metro_stations = parsed_address['metro_stations']
                address.raw = address_raw
                
                logger.debug(f"Parsed address: city={address.city}, metro={address.metro_stations}, street={address.street}, building={address.building}")
            
            # === ИЗВЛЕКАЕМ КООРДИНАТЫ ДЛЯ КАРТЫ ===
            lat, lng = self._extract_coordinates(soup)
            if lat and lng:
                address.lat = lat
                address.lng = lng
                logger.info(f"Found coordinates: {lat}, {lng}")
            
            # === ЯЗЫКИ ===
            languages = []
            lang_container = soup.find(['div', 'p'], text=re.compile(r'Знание языков|Languages', re.I))
            if lang_container and lang_container.parent:
                lang_elements = lang_container.parent.find_all(['p', 'li'])
                for lang_elem in lang_elements:
                    lang_text = lang_elem.get_text(strip=True)
                    if lang_text and 'Знание языков' not in lang_text and 'Languages' not in lang_text:
                        parts = re.split(r'[-—–]', lang_text)
                        if len(parts) >= 2:
                            languages.append({
                                'name': parts[0].strip(),
                                'level': parts[1].strip()
                            })
                        elif lang_text:
                            languages.append({
                                'name': lang_text.strip(),
                                'level': None
                            })
            
            # === ДАТА ПУБЛИКАЦИИ ===
            published_at = None
            date_selectors = [
                'p[data-qa="vacancy-creation-time"]',
                'p[data-qa="vacancy-view-creation-date"]',
                'span.vacancy-creation-time'
            ]
            
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    date_text = re.sub(r'([Рр]азмещено|[Оо]публиковано|[Вв]акансия размещена)\s*', '', date_text).strip()
                    published_at = date_text
                    break
            
            if not published_at and json_ld and 'datePosted' in json_ld:
                published_at = json_ld['datePosted']
            
            # === СОЗДАЕМ ОБЪЕКТ ВАКАНСИИ ===
            vacancy = Vacancy(
                id=vacancy_id,
                name=name,
                url=url,
                employer=employer,
                published_at=published_at,
                created_at=datetime.now().isoformat(),
                description_html=description_html,
                description_text=description_text,
                key_skills=key_skills,
                salary=salary,
                experience_id=experience_id,
                experience_name=experience_name,
                schedule_id=schedule_id,
                schedule_name=schedule_name,
                employment_id=employment_id,
                employment_name=employment_name,
                address=address,
                languages=languages
            )
            
            # Конвертируем в словарь, убирая None значения и пустые списки
            result = asdict(vacancy)
            result = self._clean_dict(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing vacancy page {url}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _clean_dict(self, d: Dict) -> Dict:
        """Очистка словаря от None значений и пустых структур"""
        if not isinstance(d, dict):
            return d
        
        cleaned = {}
        for key, value in d.items():
            if value is not None:
                if isinstance(value, dict):
                    cleaned_value = self._clean_dict(value)
                    if cleaned_value:
                        cleaned[key] = cleaned_value
                elif isinstance(value, list):
                    if value:
                        cleaned_list = []
                        for item in value:
                            if isinstance(item, dict):
                                cleaned_item = self._clean_dict(item)
                                if cleaned_item:
                                    cleaned_list.append(cleaned_item)
                            else:
                                cleaned_list.append(item)
                        if cleaned_list:
                            cleaned[key] = cleaned_list
                elif value != "":
                    cleaned[key] = value
        
        return cleaned
    
    def save_to_json(self, vacancies: List[Dict], filename: str = "rabota_vacancies.json"):
        """Сохранение вакансий в JSON файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'meta': {
                        'source': 'rabota.by',
                        'parsed_at': datetime.now().isoformat(),
                        'total_vacancies': len(vacancies)
                    },
                    'vacancies': vacancies
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Saved {len(vacancies)} vacancies to {filename}")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving to JSON: {e}")
            return False
    
    def close(self):
        """Закрытие сессии"""
        if self.session:
            self.session.close()


def main():
    """Основная функция"""
    print("=" * 60)
    print("🚀 Starting rabota.by parser (final version)")
    print("=" * 60)
    
    # Создаем парсер
    parser = RabotaByParser()
    
    try:
        # Парсим вакансии
        print("\n📋 Fetching vacancies...")
        vacancies = parser.parse_vacancy_list(
            search_text="программист",
            area="16"  # Беларусь
        )
        
        if vacancies:
            print(f"\n✅ Successfully parsed {len(vacancies)} vacancies")
            
            # Сохраняем в JSON
            parser.save_to_json(vacancies, "rabota_vacancies.json")
            
            # === СТАТИСТИКА ===
            print("\n" + "=" * 60)
            print("📊 СТАТИСТИКА ПАРСИНГА")
            print("=" * 60)
            
            # Подсчет полей
            fields_stats = {
                '💰 С зарплатой': 0,
                '🎯 С ключевыми навыками': 0,
                '📍 С координатами': 0,
                '🚇 С метро': 0,
                '🌐 С языками': 0,
                '👔 С опытом': 0,
                '🏢 С работодателем': 0,
                '📝 С описанием': 0
            }
            
            for v in vacancies:
                if v.get('salary'):
                    fields_stats['💰 С зарплатой'] += 1
                if v.get('key_skills'):
                    fields_stats['🎯 С ключевыми навыками'] += 1
                if v.get('address', {}).get('lat'):
                    fields_stats['📍 С координатами'] += 1
                if v.get('address', {}).get('metro_stations'):
                    fields_stats['🚇 С метро'] += 1
                if v.get('languages'):
                    fields_stats['🌐 С языками'] += 1
                if v.get('experience_id'):
                    fields_stats['👔 С опытом'] += 1
                if v.get('employer', {}).get('name'):
                    fields_stats['🏢 С работодателем'] += 1
                if v.get('description_text'):
                    fields_stats['📝 С описанием'] += 1
            
            for field, count in fields_stats.items():
                percentage = (count * 100) // len(vacancies) if len(vacancies) > 0 else 0
                bar = '█' * (percentage // 10) + '░' * (10 - percentage // 10)
                print(f"{field:25} [{bar}] {count}/{len(vacancies)} ({percentage}%)")
            
            # === ПРИМЕРЫ ВАКАНСИЙ ===
            print("\n" + "=" * 60)
            print("📄 ПРИМЕРЫ ВАКАНСИЙ")
            print("=" * 60)
            
            for i, v in enumerate(vacancies[:3], 1):
                print(f"\n{i}. {v.get('name', 'Без названия')}")
                print("-" * 40)
                
                if v.get('employer', {}).get('name'):
                    trusted = "✅" if v.get('employer', {}).get('trusted') else ""
                    print(f"   🏢 Компания: {v['employer']['name']} {trusted}")
                
                if v.get('salary'):
                    sal = v['salary']
                    salary_str = ""
                    if sal.get('from_value'):
                        salary_str = f"от {sal['from_value']:,}"
                    if sal.get('to_value'):
                        if salary_str:
                            salary_str += f" до {sal['to_value']:,}"
                        else:
                            salary_str = f"до {sal['to_value']:,}"
                    salary_str += f" {sal.get('currency', 'BYN')}"
                    if sal.get('gross'):
                        salary_str += " (gross)"
                    print(f"   💰 Зарплата: {salary_str}")
                
                print(f"   👔 Опыт: {v.get('experience_name', 'Не указан')}")
                print(f"   📅 График: {v.get('schedule_name', 'Не указан')}")
                
                if v.get('key_skills'):
                    skills_preview = v['key_skills'][:5]
                    if len(v['key_skills']) > 5:
                        skills_preview.append(f"... +{len(v['key_skills']) - 5}")
                    print(f"   🎯 Ключевые навыки: {', '.join(skills_preview)}")
                
                if v.get('address'):
                    addr = v['address']
                    addr_parts = []
                    if addr.get('city'):
                        addr_parts.append(f"г. {addr['city']}")
                    if addr.get('metro_stations'):
                        addr_parts.append(f"м. {', '.join(addr['metro_stations'])}")
                    if addr.get('street'):
                        addr_parts.append(addr['street'])
                    if addr.get('building'):
                        addr_parts.append(addr['building'])
                    
                    if addr_parts:
                        print(f"   📍 Адрес: {', '.join(addr_parts)}")
                    
                    if addr.get('lat') and addr.get('lng'):
                        print(f"   🗺️  Координаты: {addr['lat']:.6f}, {addr['lng']:.6f}")
                
                if v.get('languages'):
                    langs = [f"{l['name']}" + (f" ({l['level']})" if l.get('level') else "") 
                            for l in v['languages']]
                    print(f"   🌐 Языки: {', '.join(langs)}")
                
                print(f"   🔗 URL: {v.get('url', '')}")
        else:
            print("\n❌ Вакансии не найдены")
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        parser.close()
        print("\n" + "=" * 60)
        print("✅ Парсер завершил работу")
        print("=" * 60)


if __name__ == "__main__":
    main()