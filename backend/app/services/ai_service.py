"""
Сервис для работы с AI API (Nebius AI)
"""
import requests
import time
from typing import Optional, Dict, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class AIService:
    """Сервис для взаимодействия с AI API"""
    
    def __init__(self):
        self.api_key = settings.NEBius_API_KEY
        self.api_url = settings.NEBius_API_URL
        self.model = settings.NEBius_MODEL
    
    def _make_request(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7, retries: int = 2) -> Optional[str]:
        """Выполняет запрос к AI API с retry логикой"""
        if not self.api_key:
            logger.error("NEBius API key is not set")
            raise ValueError("AI API key is not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        last_exception = None
        
        for attempt in range(retries + 1):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                    logger.info(f"Retrying AI request (attempt {attempt + 1}/{retries + 1}) after {wait_time}s...")
                    time.sleep(wait_time)
                
                logger.info(f"Making AI request to {self.api_url} (attempt {attempt + 1}/{retries + 1})")
                # Увеличиваем timeout до 180 секунд для больших промптов
                response = requests.post(
                    self.api_url, 
                    headers=headers, 
                    json=data, 
                    timeout=(30, 180)  # (connect timeout, read timeout)
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    logger.info("AI request successful")
                    return content
                else:
                    error_msg = f"AI API error: {response.status_code} - {response.text[:200]}"
                    logger.error(error_msg)
                    last_exception = Exception(error_msg)
                    # Не retry для ошибок 4xx (клиентские ошибки)
                    if 400 <= response.status_code < 500:
                        raise last_exception
                        
            except requests.exceptions.Timeout as e:
                logger.warning(f"AI API request timeout (attempt {attempt + 1}/{retries + 1}): {str(e)}")
                last_exception = Exception(f"AI API request timed out. The request is taking too long. Please try again.")
                if attempt == retries:
                    raise last_exception
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"AI API request failed (attempt {attempt + 1}/{retries + 1}): {str(e)}")
                last_exception = Exception(f"Failed to connect to AI API: {str(e)}")
                if attempt == retries:
                    raise last_exception
        
        # Если дошли сюда, значит все попытки исчерпаны
        raise last_exception or Exception("AI API request failed after all retries")
    
    def generate_cover_letter(
        self,
        resume_data: Dict[str, Any],
        vacancy_data: Dict[str, Any],
        tone: str = "professional"
    ) -> str:
        """Генерирует сопроводительное письмо на основе резюме и вакансии"""
        from app.prompts import COVER_LETTER_PROMPT
        
        # Форматируем опыт работы
        work_experience_text = ""
        if resume_data.get("work_experience"):
            if isinstance(resume_data["work_experience"], list):
                for exp in resume_data["work_experience"]:
                    if isinstance(exp, dict):
                        work_experience_text += f"\n- {exp.get('position', '')} в {exp.get('company', '')} ({exp.get('period', '')}): {exp.get('description', '')}"
            else:
                work_experience_text = str(resume_data["work_experience"])
        
        # Форматируем навыки
        skills_text = resume_data.get("skills_summary", "")
        if resume_data.get("skills") and isinstance(resume_data["skills"], list):
            skills_list = [skill.get("name", skill) if isinstance(skill, dict) else str(skill) for skill in resume_data["skills"]]
            skills_text = ", ".join(skills_list) if skills_list else skills_text
        
        # Форматируем навыки вакансии
        vacancy_skills_text = ""
        if vacancy_data.get("skills") and isinstance(vacancy_data["skills"], list):
            vacancy_skills_text = ", ".join([str(skill) for skill in vacancy_data["skills"]])
        
        # Получаем текст из PDF
        pdf_text = resume_data.get("pdf_text", "")
        if not pdf_text:
            pdf_text = "Текст резюме из PDF не доступен."
        
        prompt = COVER_LETTER_PROMPT.format(
            first_name=resume_data.get("first_name", ""),
            last_name=resume_data.get("last_name", ""),
            position=resume_data.get("position", "Не указано"),
            experience_years=resume_data.get("experience_years", "Не указано"),
            about=resume_data.get("about", "Не указано"),
            education=resume_data.get("education", "Не указано"),
            skills=skills_text or "Не указано",
            work_experience=work_experience_text or "Не указано",
            pdf_text=pdf_text,
            vacancy_name=vacancy_data.get("name", ""),
            employer_name=vacancy_data.get("employer_name", ""),
            vacancy_description=vacancy_data.get("description", ""),
            vacancy_experience=vacancy_data.get("experience_name", "Не указано"),
            vacancy_employment=vacancy_data.get("employment_name", "Не указано"),
            vacancy_skills=vacancy_skills_text or "Не указано",
            tone=tone
        )
        
        return self._make_request(prompt, max_tokens=2048, temperature=0.7)
    
    def improve_resume(
        self,
        resume_data: Dict[str, Any],
        vacancy_data: Dict[str, Any]
    ) -> str:
        """Предоставляет рекомендации по улучшению резюме для конкретной вакансии"""
        from app.prompts import IMPROVE_RESUME_PROMPT
        
        # Форматируем опыт работы
        work_experience_text = ""
        if resume_data.get("work_experience"):
            if isinstance(resume_data["work_experience"], list):
                for exp in resume_data["work_experience"]:
                    if isinstance(exp, dict):
                        work_experience_text += f"\n- {exp.get('position', '')} в {exp.get('company', '')} ({exp.get('period', '')}): {exp.get('description', '')}"
            else:
                work_experience_text = str(resume_data["work_experience"])
        
        # Форматируем навыки
        skills_text = resume_data.get("skills_summary", "")
        if resume_data.get("skills") and isinstance(resume_data["skills"], list):
            skills_list = [skill.get("name", skill) if isinstance(skill, dict) else str(skill) for skill in resume_data["skills"]]
            skills_text = ", ".join(skills_list) if skills_list else skills_text
        
        # Форматируем навыки вакансии
        vacancy_skills_text = ""
        if vacancy_data.get("skills") and isinstance(vacancy_data["skills"], list):
            vacancy_skills_text = ", ".join([str(skill) for skill in vacancy_data["skills"]])
        
        # Получаем текст из PDF
        pdf_text = resume_data.get("pdf_text", "")
        if not pdf_text:
            pdf_text = "Текст резюме из PDF не доступен."
        
        prompt = IMPROVE_RESUME_PROMPT.format(
            first_name=resume_data.get("first_name", ""),
            last_name=resume_data.get("last_name", ""),
            position=resume_data.get("position", "Не указано"),
            experience_years=resume_data.get("experience_years", "Не указано"),
            about=resume_data.get("about", "Не указано"),
            education=resume_data.get("education", "Не указано"),
            skills=skills_text or "Не указано",
            work_experience=work_experience_text or "Не указано",
            pdf_text=pdf_text,
            vacancy_name=vacancy_data.get("name", ""),
            employer_name=vacancy_data.get("employer_name", ""),
            vacancy_description=vacancy_data.get("description", ""),
            vacancy_experience=vacancy_data.get("experience_name", "Не указано"),
            vacancy_employment=vacancy_data.get("employment_name", "Не указано"),
            vacancy_skills=vacancy_skills_text or "Не указано"
        )
        
        return self._make_request(prompt, max_tokens=3072, temperature=0.7)


# Глобальный экземпляр сервиса
ai_service = AIService()

