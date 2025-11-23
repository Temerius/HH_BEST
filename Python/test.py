import requests
import json
from datetime import datetime

def fetch_vacancies(text="Python", area=1, pages=1, per_page=20, outfile="vacancies.json"):
    """
    Забирает вакансии с hh.ru API и сохраняет в JSON.
    
    :param text: поисковый запрос (например, "Python")
    :param area: регион (1 = Москва, 16 = Санкт-Петербург и т.д.)
    :param pages: сколько страниц выгрузить
    :param per_page: сколько вакансий на страницу (макс. 100)
    :param outfile: имя файла для сохранения
    """
    base_url = "https://api.hh.ru/vacancies"
    all_vacancies = []

    for page in range(pages):
        params = {
            "text": text,
            "area": area,
            "page": page,
            "per_page": per_page
        }
        resp = requests.get(base_url, params=params)
        resp.raise_for_status()
        data = resp.json()

        # добавляем вакансии
        all_vacancies.extend(data.get("items", []))

        print(f"Страница {page+1} загружена, вакансий: {len(data.get('items', []))}")

    # сохраняем в файл
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(all_vacancies, f, ensure_ascii=False, indent=2)

    print(f"Итого сохранено {len(all_vacancies)} вакансий в {outfile}")


if __name__ == "__main__":
    # пример: выгрузим 2 страницы по 20 вакансий "Python" в Москве
    fetch_vacancies(text="Python", area=1, pages=2, per_page=20, outfile=f"vacancies_{datetime.now().date()}.json")
