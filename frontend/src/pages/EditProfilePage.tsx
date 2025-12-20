import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import api from '../services/api'
import { User, UserSkill, Skill } from '../types'

// Словарь навыков по категориям
const SKILLS_DICT: Record<string, string[]> = {
  "Языки программирования": [
    "c++", "c#", "с#", "с++", "java", "java 8+", "java 8+,", "python", "javascript", 
    "java script", "js", "typescript", "php", "php5", "php7+", "php8", "go", "golang", 
    "rust", "kotlin", "swift", "objective-c", "scala", "lua", "pascal", "delphi", 
    "borland delphi", "dart", "solidity", "abap"
  ],
  
  "Фреймворки и библиотеки": [
    "spring", "spring boot", "spring framework", "spring mvc", "spring security", 
    "spring data", "spring aspect", "spring webflux", "spring cloud", "django", 
    "django framework", "django rest framework", "flask", "fastapi", "laravel", 
    "symfony", ".net", ".net framework", ".net core", "asp.net", "asp.net core", 
    "entity framework", "hibernate", "mybatis", "express", "nest", "micronaut", 
    "unity", "unreal engine"
  ],
  
  "Frontend технологии": [
    "react", "react.js", "react native", "vue", "vue.js", "vue2", "vuejs", "vuex", 
    "pinia", "angular", "angularjs", "svelte", "next", "next.js", "nuxt", "nuxtjs", 
    "html", "html5", "css", "css3", "scss", "sass", "tailwind", "tailwind css", 
    "bootstrap", "material design", "jquery", "iquery", "ajax", "aiax", "three.js", 
    "3js", "pixi.js", "webgl", "rxjs", "rxswift", "rxcocoa", "rxmoya", "redux", "ngrx", 
    "webpack", "gulp", "vite", "babel", "composition api", "web workers", "бэм", "bem"
  ],
  
  "Backend технологии": [
    "node.js", "rest api", "restful api", "graphql", "grpc", "soap", "websocket", 
    "websockets", "web socket", "api", "web api", "json api", "odata", "microservices", 
    "микросервисы", "soa", "mvc", "mvvm", "oop", "ооп", "solid", "design patterns", 
    "webflux", "project reactor"
  ],
  
  "Базы данных": [
    "sql", "mysql", "postgresql", "ms sql", "ms sql server", "oracle", "oracle database", 
    "oracle pl/sql", "mongodb", "redis", "elasticsearch", "clickhouse", "cassandra", 
    "dynamodb", "sqlite", "nosql", "субд", "базы данных", "основы баз данных", 
    "работа с базами данных", "cистемы управления базами данных", "transact-sql", 
    "pl/sql", "pl/pgsql", "teradata", "dbf"
  ],
  
  "1С технологии": [
    "1с", "1с: предприятие", "1с: предприятие 7", "1с: предприятие 8", "1c:предприятия 8.3", 
    "1с: бухгалтерия", "1c: бухгалтерия", "1с: торговля", "1с: управление торговлей", 
    "1с: документооборот", "1с: производство", "1с: управление производственным предприятием", 
    "1с: зарплата и управление персоналом", "1c: зарплата и кадры", "1с: комплексная автоматизация", 
    "1с: розница", "1с: управление предприятием", "1с: управление персоналом", "1с: экономист", 
    "1c:сrm", "1c: erp", "1с:ут", "1с программирование", "разработка 1с", "тестирование 1с", 
    "создание конфигурации 1с", "обновление конфигурации 1с", "интеграция 1с", 
    "доработка типовых конфигураций", "скд", "1с скд", "erp-системы на базе 1с", "знание 1с"
  ],
  
  "DevOps и инфраструктура": [
    "docker", "docker-compose", "kubernetes", "helm", "helm charts", "jenkins", "ci/cd", 
    "terraform", "ansible", "vagrant", "aws", "amazon web services", "azure", "gcp", 
    "nginx", "apache", "git", "github", "gitlab", "svn", "bitbucket", "linux", 
    "linux kernel", "windows", "windows 7", "windows 8", "windows xp", "ос windows"
  ],
  
  "Тестирование": [
    "unit testing", "unit/e2e tests", "unit, integration, e2e", "junit", "jest", 
    "jasmine", "karma", "mockito", "pytest", "unittest", "phpunit", "selenium", 
    "postman", "test case", "test pyramid", "tdd", "функциональное тестирование", 
    "интеграционное тестирование", "регрессионное тестирование", "тестирование и отладка кода", 
    "check-list"
  ],
  
  "Мобильная разработка": [
    "android", "android sdk", "ios", "ios sdk", "flutter", "react native", "ionic", 
    "xcode", "android studio", "kotlin", "swift", "objective-c", "ndk", "разработчик мобильных приложений"
  ],
  
  "AI/ML и Data Science": [
    "ai", "ml", "llm", "ai api", "ai models", "ai/ml", "machine learning", "deep learning", 
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy", "opencv", 
    "data scientist", "big data", "анализ данных", "аналитика", "cuda", "onnx", 
    "ml forensics", "prompt engineering"
  ],
  
  "Blockchain и Web3": [
    "blockchain", "ethereum", "evm", "revm", "solidity", "web3.js", "smart contracts", 
    "defi", "dex", "cex", "foundry"
  ],
  
  "Игровая разработка": [
    "unity", "unreal engine", "gamedev", "game programming", "разработка компьютерных игр", 
    "программирование 3d-графики", "гейм-дизайн", "разработка игровых механик", 
    "zenject", "dotween", "unitask"
  ],
  
  "Инженерные системы и CAD": [
    "autocad", "solidworks", "autodesk revit", "autodesk 3ds max", "altium designer", 
    "scada", "mes", "plc", "modbus", "схемотехника электронного оборудования", 
    "инженерные системы", "чтение чертежей", "станки чпу", "arm", "x86", "stm32", 
    "микроконтроллер stm", "микроконтроллер microchip", "микроконтроллер texas instrument"
  ],
  
  "SAP технологии": [
    "sap", "sap erp", "sap bi", "sap bw", "bw4hana", "sap fiory", "fiori", 
    "sapui5", "sap business objects", "sap project", "sap bopf", "sap cds", "btp"
  ],
  
  "CMS и конструкторы": [
    "wordpress", "cms wordpress", "drupal", "cms drupal", "drupal api", "joomla cms", 
    "modx", "umbraco cms", "bitrix", "битрикс24", "1с-битрикс", "shopify", "gutenberg"
  ],
  
  "Бизнес-навыки": [
    "управление проектами", "project management", "agile", "agile/scrum", "scrum", 
    "agile project management", "управление командой", "управление процессами", 
    "управление бюджетом", "бизнес-анализ", "business development", "business modeling", 
    "анализ бизнес-процессов", "оптимизация бизнес-процессов", "моделирование бизнес-процессов", 
    "описание бизнес-процессов", "автоматизация бизнес-процессов", "автоматизация процессов", 
    "автоматизация производства", "разработка бизнес-требований", "сбор требований", 
    "use case", "user stories", "bpmn", "uml"
  ],
  
  "Маркетинг и продажи": [
    "основы маркетинга", "b2b-маркетинг", "аффилейт-маркетинг", "контекстная реклама", 
    "яндекс.директ", "яндекс.метрика", "google analytics", "стратегия продаж", 
    "активные продажи", "холодные продажи", "b2b продажи", "развитие продаж", 
    "анализ продаж", "аналитика продаж", "sales skills", "sales management", 
    "управление ассортиментом", "анализ рынка", "анализ конкурентной среды", 
    "e-commerce", "crm", "управление отношениями с клиентами", "поиск и привлечение клиентов"
  ],
  
  "Soft skills": [
    "коммуникативные навыки", "communication skills", "навыки переговоров", 
    "навыки презентации", "presentation skills", "проведение презентаций", 
    "умение работать в коллективе", "работа в команде", "teamplayer", 
    "лидерские качества", "leadership skills", "стрессоустойчивость", 
    "эмоциональная устойчивость", "ответственность", "ответственность и пунктуальность", 
    "пунктуальность", "исполнительность", "многозадачность", "работа в условиях многозадачности", 
    "умение учиться", "creativity", "creative writing", "аналитическое мышление", 
    "системное мышление", "умение аналитически мыслить", "математический склад ума", 
    "бесконфликтность", "умение проявлять внимание, заинтересованность, дружелюбие"
  ],
  
  "Языки": [
    "английский язык", "business english", 
    "немецкий язык", "испанский язык", "итальянский язык", "русский язык"
  ],
  
  "Документация и стандарты": [
    "техническая документация", "работа с технической документацией", 
    "умение читать техническую документацию", "чтение проектной документации", 
    "разработка пользовательской документации", "разработка инструкций", 
    "разработка технических заданий", "гост", "ескд", "корпоративная этика", 
    "деловая переписка", "деловое общение", "деловая коммуникация", "грамотность", 
    "грамотная речь", "техническая грамотность"
  ],
  
  "Системное администрирование": [
    "администрирование серверов linux", "администрирование серверов windows", 
    "системное программирование", "system software", "системная интеграция", 
    "системный анализ", "мониторинг серверов", "мониторинг сети", "настройка пк", 
    "настройка по", "настройка сетевых подключений", "ремонт пк", "tcp/ip", "tcp", 
    "http", "https", "ftp", "dns", "dhcp", "vpn", "информационная безопасность", 
    "управление информационной безопасностью", "уязвимости программного обеспечения"
  ],
  
  "Инструменты разработки": [
    "visual studio", "visual studio code", "ms visual studio", "intellij idea", 
    "pycharm", "phpstorm", "webstorm", "eclipse", "netbeans", "atom", "sublime text", 
    "vim", "emacs", "xcode", "android studio", "devtools", "swagger", "figma", 
    "zeplin", "adobe photoshop", "sketch", "jira", "atlassian jira", "confluence", 
    "redmine", "trello", "slack", "teams", "zoom"
  ],
  
  "Другие технологии": [
    "rpa", "itsm", "dwh", "etl", "bi", "power bi", "tableau", "sas", "grafana", 
    "prometheus", "apache airflow", "apache kafka", "kafka", "rabbitmq", "activemq", 
    "artemis", "jms", "celery", "asyncio", "threading", "multiprocessing", 
    "websockets", "grpc", "graphql", "odata", "json", "xml", "yaml", "linq", 
    "lambda", "jasperreports", "keycloak", "oauth", "jwt", "ssl/tls", "https", 
    "wcf", "mfc", "qt", "qml", "gtk", "wxwidgets", "electron", "ionic", "cordova", 
    "phonegap", "xamarin", "maui", "blazor", "razor pages", "webassembly", "wasm"
  ],
  
  "Прочие навыки": [
    "full-stack", "фулл-стэк", "full stack", "frontend", "front-end", "backend", 
    "веб-программирование", "web application development", "веб-дизайн", "design", 
    "ui/ux", "pixel-perfect", "ssr", "spa", "pwa", "responsive design", "mobile", 
    "cloud", "devops", "qa", "код-ревью", "оптимизация кода", "структуры данных", 
    "алгоритмы", "алгоритмы и структуры данных", "линейное программирование", 
    "компьютерная грамотность", "пользователь пк", "ms excel", "ms word", 
    "ms powerpoint", "ms access", "ms visio", "ms sharepoint", "ms dynamics", 
    "office 365", "google docs", "google sheets", "работа с большим объемом информации", 
    "систематизация информации", "поиск информации в интернет", "обучение персонала", 
    "обучение и развитие", "консультирование", "техническая поддержка", 
    "бухгалтерский учет", "бухгалтерская отчетность", "управленческий учет", 
    "лизинг", "управление складом", "wms", "международные рынки", "логистика", 
    "работа с детьми", "сельское хозяйство", "машиностроение", "авторский надзор", 
    "аварийно-восстановительные работы", "создание сайтов", "анимация", 
    "мобильная аналитика", "adjust", "appsflyer", "facebook sdk", "альфа-авто", 
    "datareon", "castdev", "adam", "alloy", "branch", "moya", "mdc", "filament", 
    "yocto", "buildroot", "u-boot", "device tree", "device drivers", "разработка драйверов", 
    "rtos", "ecs", "bsp", "netplan", "modsecurity", "suricata", "chromium embedded framework", 
    "ext js", "element ui", "lerna", "vercel", "tbd", "liquibase", "sqlalchemy", 
    "psycopg", "aiogram", "pyrogram", "ros", "gis", "secure boot", "pep", "output", 
    "подготовка коммерческих предложений", "проведение переговоров с первыми лицами компании", 
    "постановка задач разработчикам", "enterprise architect", "draw.io", "flex"
  ]
}

// Захардкоженные направления (fallback)
const DEFAULT_SPECIALIZATIONS = [
  'Backend',
  'Frontend',
  'Fullstack',
  'DevOps',
  'Mobile',
  'Data Science',
  'QA',
  'Security',
  'Game Development',
  'Embedded',
  'Blockchain',
  'AI/ML',
  'Cloud Engineering',
  'Site Reliability Engineering (SRE)',
  'Database Administration',
  'System Administration',
  'Network Engineering',
  'UI/UX Design',
  'Product Management',
  'Technical Writing',
  'DevOps Engineering',
  'Platform Engineering',
  'Data Engineering'
]

// Преобразуем словарь в массив навыков для использования в компоненте
const getAllSkillsFromDict = (): Array<{ name: string; category: string }> => {
  const skills: Array<{ name: string; category: string }> = []
  Object.entries(SKILLS_DICT).forEach(([category, skillList]) => {
    skillList.forEach(skill => {
      skills.push({ name: skill, category })
    })
  })
  return skills
}

// Получаем список категорий из словаря
const getCategoriesFromDict = (): string[] => {
  return Object.keys(SKILLS_DICT)
}

export default function EditProfilePage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const [user, setUser] = useState<User | null>(null)
  const [userSkills, setUserSkills] = useState<UserSkill[]>([])
  const [availableSkills, setAvailableSkills] = useState<any[]>([])
  const [skillCategories, setSkillCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [searchSkill, setSearchSkill] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [specializations, setSpecializations] = useState<string[]>([])
  
  // Локальное состояние для изменений (не применяется до сохранения)
  const [localUser, setLocalUser] = useState<User | null>(null)
  const [allSkills, setAllSkills] = useState<any[]>([])

  const filterSkills = useCallback((skills: any[], search: string, category: string) => {
    let filtered = skills
    
    // Сначала фильтруем по категории, если выбрана
    if (category) {
      filtered = filtered.filter((skill: any) => 
        skill.category === category
      )
    } else {
      // Если категория не выбрана, убираем дубликаты (оставляем первую встреченную категорию)
      const seen = new Set<string>()
      filtered = filtered.filter((skill: any) => {
        if (seen.has(skill.name.toLowerCase())) {
          return false
        }
        seen.add(skill.name.toLowerCase())
        return true
      })
    }
    
    // Затем фильтруем по поиску
    if (search) {
      filtered = filtered.filter((skill: any) => 
        skill.name.toLowerCase().includes(search.toLowerCase())
      )
    }
    
    setAvailableSkills(filtered)
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [userResponse, mySkillsResponse, specializationsResponse] = await Promise.all([
        api.get('/api/users/me'),
        api.get('/api/skills/my'),
        api.get('/api/metadata/specializations')
      ])
      setUser(userResponse.data)
      setLocalUser({ ...userResponse.data }) // Копируем для локального редактирования
      setUserSkills(mySkillsResponse.data || [])
      // Используем данные из API или fallback значения
      setSpecializations(specializationsResponse.data && specializationsResponse.data.length > 0 
        ? specializationsResponse.data 
        : DEFAULT_SPECIALIZATIONS)
      
      // Используем словарь для навыков и категорий
      const skills = getAllSkillsFromDict()
      const categories = getCategoriesFromDict()
      setSkillCategories(categories)
      setAllSkills(skills)
      
      // Фильтруем навыки по поиску и категории (только если уже есть значения)
      if (searchSkill || selectedCategory) {
        filterSkills(skills, searchSkill, selectedCategory)
      } else {
        setAvailableSkills(skills)
      }
    } catch (error) {
      console.error('Error loading data:', error)
      alert('Ошибка при загрузке данных')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      navigate('/login')
      return
    }
    loadData()
  }, [])

  useEffect(() => {
    // Фильтруем только если навыки уже загружены
    if (allSkills.length > 0 && !loading) {
      filterSkills(allSkills, searchSkill, selectedCategory)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchSkill, selectedCategory])

  const handleUpdateUser = (field: string, value: any) => {
    // Обновляем только локальное состояние
    if (localUser) {
      setLocalUser({ ...localUser, [field]: value })
    }
  }

  const handleSaveUser = async () => {
    if (!localUser) return
    
    try {
      setSaving(true)
      const response = await api.put('/api/users/me', {
        specialization: localUser.specialization
      })
      setUser(response.data)
      setLocalUser({ ...response.data })
      alert('Профиль успешно сохранен')
    } catch (error) {
      console.error('Error updating user:', error)
      alert('Ошибка при обновлении профиля')
    } finally {
      setSaving(false)
    }
  }

  const handleAddSkill = async (skillName: string, skillCategory?: string) => {
    try {
      const response = await api.post('/api/skills/my', {
        skill_name: skillName,
        skill_category: skillCategory,
        level: 'intermediate',
        years_of_experience: null
      })
      // Обновляем локальное состояние без перезагрузки
      const newSkill: UserSkill = {
        skill_id: response.data.skill_id || response.data.id,
        skill_name: skillName,
        skill_category: skillCategory,
        level: 'intermediate',
        years_of_experience: undefined
      }
      setUserSkills([...userSkills, newSkill])
    } catch (error: any) {
      if (error.response?.status === 400) {
        alert('Этот навык уже добавлен')
      } else {
        console.error('Error adding skill:', error)
        alert('Ошибка при добавлении навыка')
      }
    }
  }

  const handleRemoveSkill = async (skillId: number) => {
    try {
      await api.delete(`/api/skills/my/${skillId}`)
      // Обновляем локальное состояние без перезагрузки
      setUserSkills(userSkills.filter(skill => skill.skill_id !== skillId))
    } catch (error) {
      console.error('Error removing skill:', error)
      alert('Ошибка при удалении навыка')
    }
  }

  const handleUpdateSkill = async (skillId: number, level: string, years?: number) => {
    try {
      await api.put(`/api/skills/my/${skillId}`, {
        level,
        years_of_experience: years
      })
      // Обновляем локальное состояние без перезагрузки
      setUserSkills(userSkills.map(skill => 
        skill.skill_id === skillId 
          ? { ...skill, level, years_of_experience: years }
          : skill
      ))
    } catch (error) {
      console.error('Error updating skill:', error)
      alert('Ошибка при обновлении навыка')
    }
  }


  if (loading) {
    return (
      <div className={`text-center py-12 transition-colors ${
        isDark ? 'text-gray-300' : 'text-gray-600'
      }`}>Загрузка...</div>
    )
  }

  return (
    <div className="px-4 py-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className={`text-3xl font-bold transition-colors ${
          isDark ? 'text-white' : 'text-gray-900'
        }`}>Редактирование профиля</h1>
        <Link
          to="/profile"
          className={`px-4 py-2 rounded-lg transition-colors ${
            isDark
              ? 'bg-gray-700 text-gray-200 hover:bg-gray-600'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Назад к профилю
        </Link>
      </div>

      {localUser && (
        <>
          {/* Основная информация */}
          <div className={`rounded-lg shadow-sm p-6 mb-6 transition-colors ${
            isDark 
              ? 'bg-gray-800/50 border border-gray-700' 
              : 'bg-white'
          }`}>
            <div className="flex justify-between items-center mb-4">
              <h2 className={`text-xl font-semibold transition-colors ${
                isDark ? 'text-white' : 'text-gray-900'
              }`}>Основная информация</h2>
              <button
                onClick={handleSaveUser}
                disabled={saving}
                className={`px-6 py-2 rounded-lg transition-colors ${
                  isDark
                    ? 'bg-green-600 hover:bg-green-700 text-white'
                    : 'bg-green-500 hover:bg-green-600 text-white'
                } disabled:opacity-50`}
              >
                {saving ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className={`block text-sm font-medium mb-1 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  Направление разработки
                </label>
                <select
                  value={localUser?.specialization || ''}
                  onChange={(e) => handleUpdateUser('specialization', e.target.value || null)}
                  className={`w-full px-3 py-2 border rounded-lg transition-colors ${
                    isDark
                      ? 'border-gray-600 bg-gray-700/50 text-white'
                      : 'border-gray-300 bg-white text-gray-900'
                  }`}
                >
                  <option value="">Не выбрано</option>
                  {specializations.map(spec => (
                    <option key={spec} value={spec}>{spec}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Навыки */}
          <div className={`rounded-lg shadow-sm p-6 mb-6 transition-colors ${
            isDark 
              ? 'bg-gray-800/50 border border-gray-700' 
              : 'bg-white'
          }`}>
            <h2 className={`text-xl font-semibold mb-4 transition-colors ${
              isDark ? 'text-white' : 'text-gray-900'
            }`}>Мои навыки</h2>

            {/* Поиск навыков */}
            <div className="mb-4 space-y-2">
              <input
                type="text"
                placeholder="Поиск навыков..."
                value={searchSkill}
                onChange={(e) => setSearchSkill(e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg transition-colors ${
                  isDark
                    ? 'border-gray-600 bg-gray-700/50 text-white placeholder-gray-400'
                    : 'border-gray-300 bg-white text-gray-900 placeholder-gray-500'
                }`}
              />
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg transition-colors ${
                  isDark
                    ? 'border-gray-600 bg-gray-700/50 text-white'
                    : 'border-gray-300 bg-white text-gray-900'
                }`}
              >
                <option value="">Все категории</option>
                {skillCategories.map(category => (
                  <option key={category} value={category}>
                    {category.charAt(0).toUpperCase() + category.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            {/* Мои навыки */}
            {userSkills.length > 0 && (
              <div className="mb-6">
                <h3 className={`text-lg font-medium mb-3 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>Добавленные навыки:</h3>
                <div className="flex flex-wrap gap-2">
                  {userSkills.map((userSkill) => (
                    <div
                      key={userSkill.skill_id}
                      className={`px-3 py-2 rounded-lg border transition-colors ${
                        isDark
                          ? 'bg-gray-700/50 border-gray-600'
                          : 'bg-gray-100 border-gray-300'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className={`font-medium ${
                          isDark ? 'text-white' : 'text-gray-900'
                        }`}>{userSkill.skill_name}</span>
                        <select
                          value={userSkill.level}
                          onChange={(e) => handleUpdateSkill(userSkill.skill_id, e.target.value, userSkill.years_of_experience)}
                          className={`text-xs px-2 py-1 rounded border transition-colors ${
                            isDark
                              ? 'border-gray-600 bg-gray-800 text-white'
                              : 'border-gray-300 bg-white text-gray-900'
                          }`}
                        >
                          <option value="beginner">Начальный</option>
                          <option value="intermediate">Средний</option>
                          <option value="advanced">Продвинутый</option>
                          <option value="expert">Эксперт</option>
                        </select>
                        <button
                          onClick={() => handleRemoveSkill(userSkill.skill_id)}
                          className={`text-red-500 hover:text-red-700 transition-colors ${
                            isDark ? 'hover:text-red-400' : ''
                          }`}
                        >
                          ×
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Доступные навыки */}
            <div>
              <h3 className={`text-lg font-medium mb-3 ${
                isDark ? 'text-gray-300' : 'text-gray-700'
              }`}>Доступные навыки:</h3>
              {availableSkills.length === 0 && !loading ? (
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  {searchSkill || selectedCategory ? 'Навыки не найдены' : 'Навыки не загружены'}
                </p>
              ) : (
                <div className="flex flex-wrap gap-2 max-h-64 overflow-y-auto">
                  {availableSkills
                    .filter(skill => !userSkills.find(us => us.skill_name === skill.name))
                    .map((skill) => (
                      <button
                        key={skill.name}
                        onClick={() => handleAddSkill(skill.name, skill.category)}
                        className={`px-3 py-2 rounded-lg border transition-colors ${
                          isDark
                            ? 'bg-gray-700/30 border-gray-600 text-gray-300 hover:bg-gray-700/50'
                            : 'bg-gray-50 border-gray-300 text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        {skill.name}
                      </button>
                    ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

