import requests
import json

API_KEY = "v1.CmQKHHN0YXRpY2tleS1lMDBuN2JjczNkYnh2d3E5c2oSIXNlcnZpY2VhY2NvdW50LWUwMGJmbXlkbXFxeTliYTJxZDIMCJObgsoGEMG2qbMCOgwIk56alQcQwOK54wFAAloDZTAw.AAAAAAAAAAG6vd-VTW7IsaU-MAWO2CORXFsYDBci8tfRScKL6lcmmImAydbJHmJNRWSal1j8mFpuRW80vCx6gkCHGSb_vuwF"
BASE_URL = "https://api.studio.nebius.ai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "Qwen/Qwen3-235B-A22B-Thinking-2507",
    "messages": [
        {"role": "user", "content": "Привет! Расскажи кратко о себе."}
    ],
    "max_tokens": 1024,
    "temperature": 0.7
}

response = requests.post(BASE_URL, headers=headers, json=data)

if response.status_code == 200:
    result = response.json()
    print(result["choices"][0]["message"]["content"])
else:
    print(f"Ошибка: {response.status_code}")
    print(response.text)