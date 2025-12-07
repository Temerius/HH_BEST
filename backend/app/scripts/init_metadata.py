"""
Скрипт для инициализации метаданных (навыки, направления) в Redis
"""
import json
import os
import redis

# Подключаемся к Redis напрямую, используя переменные окружения или значения по умолчанию
# Если скрипт запускается в Docker, используем 'redis' как хост по умолчанию
# Если локально, используем 'localhost'
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', 6379))
redis_db = int(os.getenv('REDIS_DB', 0))
redis_password = os.getenv('REDIS_PASSWORD') or None

redis_client = redis.Redis(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    password=redis_password,
    decode_responses=True
)

# Навыки по категориям
SKILLS = {
    "programming": [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
        "PHP", "Ruby", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl", "Lua",
        "Dart", "Haskell", "Erlang", "Elixir", "Clojure", "F#", "OCaml"
    ],
    "frameworks": [
        "React", "Vue.js", "Angular", "Next.js", "Nuxt.js", "Svelte", "Django",
        "Flask", "FastAPI", "Spring", "Express.js", "NestJS", "Laravel", "Symfony",
        "Ruby on Rails", "ASP.NET", "ASP.NET Core", ".NET", "Flutter", "React Native",
        "Xamarin", "Ionic", "Cordova"
    ],
    "databases": [
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra",
        "DynamoDB", "Oracle", "SQL Server", "SQLite", "MariaDB", "Neo4j", "InfluxDB",
        "ClickHouse", "TimescaleDB", "CouchDB", "RavenDB"
    ],
    "cloud": [
        "AWS", "Azure", "Google Cloud", "Yandex Cloud", "VK Cloud", "SberCloud",
        "Docker", "Kubernetes", "Terraform", "Ansible", "Jenkins", "GitLab CI/CD",
        "GitHub Actions", "CircleCI", "Travis CI", "TeamCity", "Bamboo"
    ],
    "tools": [
        "Git", "SVN", "Mercurial", "Jira", "Confluence", "Notion", "Figma", "Adobe XD",
        "Sketch", "Postman", "Swagger", "GraphQL", "REST API", "gRPC", "WebSocket",
        "RabbitMQ", "Apache Kafka", "Apache Spark", "Hadoop", "Airflow"
    ],
    "testing": [
        "Unit Testing", "Integration Testing", "E2E Testing", "Selenium", "Cypress",
        "Playwright", "Jest", "Pytest", "JUnit", "Mocha", "Chai", "RSpec", "TestNG"
    ],
    "mobile": [
        "iOS Development", "Android Development", "React Native", "Flutter",
        "Xamarin", "Ionic", "Swift", "Kotlin", "Objective-C", "Java (Android)"
    ],
    "data": [
        "Data Analysis", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch",
        "Scikit-learn", "Pandas", "NumPy", "Matplotlib", "Seaborn", "Jupyter",
        "Data Visualization", "ETL", "Data Warehousing", "Business Intelligence", 
        "Spark", "Hadoop", "Hive", "Pig", "Sqoop", "Flume", "Kafka", "Storm", "Flink", 
        "Beam", "Presto", "Dask", "Airflow", "Luigi", "Pinot", "Impala", "Drill"
    ],
    "security": [
        "OWASP", "Penetration Testing", "Security Auditing", "Cryptography",
        "OAuth", "JWT", "SSL/TLS", "Firewall", "VPN", "IDS/IPS"
    ],
    "other": [
        "Linux", "Windows Server", "Bash", "PowerShell", "System Administration",
        "Network Administration", "Agile", "Scrum", "Kanban", "CI/CD", "Microservices",
        "API Design", "System Design", "Architecture", "Code Review", "Mentoring"
    ]
}

# Направления разработки
SPECIALIZATIONS = [
    "Backend", "Frontend", "Fullstack", "DevOps", "Mobile", "Data Science",
    "QA", "Security", "Game Development", "Embedded", "Blockchain", "AI/ML",
    "Cloud Engineering", "Site Reliability Engineering (SRE)", "Database Administration",
    "System Administration", "Network Engineering", "UI/UX Design", "Product Management",
    "Technical Writing", "DevOps Engineering", "Platform Engineering", "Data Engineering",
]

# Категории навыков
SKILL_CATEGORIES = list(SKILLS.keys())


def init_metadata():
    """Инициализация метаданных в Redis"""
    print("Initializing metadata in Redis...")
    
    # Сохраняем навыки
    skills_list = []
    for category, skill_names in SKILLS.items():
        for skill_name in skill_names:
            skills_list.append({
                "name": skill_name,
                "category": category
            })
    
    redis_client.set("metadata:skills", json.dumps(skills_list, ensure_ascii=False))
    print(f"✓ Saved {len(skills_list)} skills")
    
    # Сохраняем направления
    redis_client.set("metadata:specializations", json.dumps(SPECIALIZATIONS, ensure_ascii=False))
    print(f"✓ Saved {len(SPECIALIZATIONS)} specializations")
    
    # Сохраняем категории
    redis_client.set("metadata:skill_categories", json.dumps(SKILL_CATEGORIES, ensure_ascii=False))
    print(f"✓ Saved {len(SKILL_CATEGORIES)} skill categories")
    
    print("Metadata initialization completed!")


if __name__ == "__main__":
    init_metadata()

