"""
Утилиты для обработки текста вакансий
"""
import re
from typing import Optional


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

