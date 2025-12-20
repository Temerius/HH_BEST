"""
Утилиты для обработки текста вакансий
"""
import re
from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
    logger.warning("PyPDF2 not installed. PDF text extraction will not work.")


def process_highlighttext(text: Optional[str]) -> Optional[str]:
    """
    Обрабатывает текст с тегами <highlighttext>...</highlighttext>
    Заменяет их на <mark>...</mark> для выделения в HTML
    """
    if not text:
        return text
    
    # Заменяем <highlighttext> на <mark class="highlight">
    # и закрывающий тег соответственно
    text = re.sub(
        r'<highlighttext>(.*?)</highlighttext>',
        r'<mark class="highlight">\1</mark>',
        text,
        flags=re.IGNORECASE | re.DOTALL
    )
    
    return text


def clean_html_text(text: Optional[str]) -> Optional[str]:
    """
    Очищает HTML текст от лишних тегов и нормализует пробелы
    """
    if not text:
        return text
    
    # Убираем множественные пробелы и переносы строк
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def extract_text_from_pdf(pdf_path: Path) -> Optional[str]:
    """
    Извлекает текст из PDF файла
    
    Args:
        pdf_path: Путь к PDF файлу
        
    Returns:
        Текст из PDF или None в случае ошибки
    """
    if not PyPDF2:
        logger.error("PyPDF2 is not installed. Cannot extract text from PDF.")
        return None
    
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return None
    
    try:
        text_parts = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num + 1}: {e}")
                    continue
        
        if not text_parts:
            logger.warning(f"No text extracted from PDF: {pdf_path}")
            return None
        
        # Объединяем текст со всех страниц
        full_text = "\n\n".join(text_parts)
        
        # Очищаем текст: убираем множественные пробелы и переносы
        full_text = re.sub(r'\s+', ' ', full_text)
        full_text = full_text.strip()
        
        logger.info(f"Successfully extracted {len(full_text)} characters from PDF: {pdf_path}")
        return full_text if full_text else None
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
        return None

