import { useState, useEffect } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import api from '../services/api'
import { VacancyListResponse } from '../types'
import VacancyCard from '../components/VacancyCard'

interface Area {
  id: string
  name: string
  parent_id?: string
}

interface MetroStation {
  id: number
  name: string
  line_name?: string
  city_id?: string
}

export default function VacanciesPage() {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const [vacancies, setVacancies] = useState<VacancyListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [searchText, setSearchText] = useState('')
  const [areas, setAreas] = useState<Area[]>([])
  const [loadingAreas, setLoadingAreas] = useState(false)
  const [metroStations, setMetroStations] = useState<MetroStation[]>([])
  const [loadingMetro, setLoadingMetro] = useState(false)
  
  const getDefaultFilters = () => ({
    area_id: '',
    salary_from: '',
    salary_currency: '',
    metro_ids: [] as number[],
    experience_id: '',
    employment_id: '',
    schedule_id: '',
    sort_by: 'published_at',
    sort_order: 'desc'
  })

  // Временные фильтры (не применяются до нажатия кнопки)
  const [tempFilters, setTempFilters] = useState(() => {
    const saved = localStorage.getItem('vacancyFilters')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        // Валидация и очистка старых значений
        const validEmploymentIds = ['', 'full', 'part', 'project', 'probation']
        if (parsed.employment_id && !validEmploymentIds.includes(parsed.employment_id)) {
          parsed.employment_id = ''
        }
        // Убеждаемся, что sort_by правильный
        const validSortBy = ['published_at', 'salary_from', 'salary_to', 'name']
        if (!validSortBy.includes(parsed.sort_by)) {
          parsed.sort_by = 'published_at'
        }
        // Убеждаемся, что sort_order правильный
        if (parsed.sort_order !== 'asc' && parsed.sort_order !== 'desc') {
          parsed.sort_order = 'desc'
        }
        // Убеждаемся, что metro_ids - массив
        if (!Array.isArray(parsed.metro_ids)) {
          parsed.metro_ids = []
        }
        return { ...getDefaultFilters(), ...parsed }
      } catch (e) {
        return getDefaultFilters()
      }
    }
    return getDefaultFilters()
  })
  
  // Примененные фильтры (используются для запросов)
  const [appliedFilters, setAppliedFilters] = useState(() => {
    const saved = localStorage.getItem('vacancyFilters')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        // Валидация и очистка старых значений
        const validEmploymentIds = ['', 'full', 'part', 'project', 'probation']
        if (parsed.employment_id && !validEmploymentIds.includes(parsed.employment_id)) {
          parsed.employment_id = ''
        }
        // Убеждаемся, что sort_by правильный
        const validSortBy = ['published_at', 'salary_from', 'salary_to', 'name']
        if (!validSortBy.includes(parsed.sort_by)) {
          parsed.sort_by = 'published_at'
        }
        // Убеждаемся, что sort_order правильный
        if (parsed.sort_order !== 'asc' && parsed.sort_order !== 'desc') {
          parsed.sort_order = 'desc'
        }
        // Убеждаемся, что metro_ids - массив
        if (!Array.isArray(parsed.metro_ids)) {
          parsed.metro_ids = []
        }
        return { ...getDefaultFilters(), ...parsed }
      } catch (e) {
        return getDefaultFilters()
      }
    }
    return getDefaultFilters()
  })
  
  const [showFilters, setShowFilters] = useState(false)
  const [showMetroDropdown, setShowMetroDropdown] = useState(false)

  // Загружаем области и метро при монтировании
  useEffect(() => {
    loadAreas()
    loadMetroStations()
  }, [])

  // Закрываем дропбокс метро при клике вне его
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (showMetroDropdown && !target.closest('.metro-dropdown-container')) {
        setShowMetroDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showMetroDropdown])

  // Загружаем вакансии при изменении примененных фильтров или страницы
  useEffect(() => {
    loadVacancies()
  }, [page, searchText, appliedFilters])

  const loadAreas = async () => {
    try {
      setLoadingAreas(true)
      // Загружаем Минск и областные центры РБ
      const response = await api.get('/api/areas', { params: { parent_id: '16' } })
      const mainAreas = response.data.filter((area: Area) => 
        area.id === '1002' || // Минск
        area.id === '1003' || // Брестская область
        area.id === '1004' || // Витебская область
        area.id === '1005' || // Гомельская область
        area.id === '1006' || // Гродненская область
        area.id === '1007' || // Минская область
        area.id === '1008'    // Могилевская область
      )
      
      // Загружаем районы для каждого областного центра
      const areasWithDistricts = [...mainAreas]
      for (const area of mainAreas) {
        if (area.id !== '1002') { // Не Минск
          try {
            const districtsResponse = await api.get('/api/areas', { params: { parent_id: area.id } })
            areasWithDistricts.push(...districtsResponse.data)
          } catch (error) {
            console.error(`Error loading districts for ${area.name}:`, error)
          }
        }
      }
      
      setAreas(areasWithDistricts)
    } catch (error) {
      console.error('Error loading areas:', error)
    } finally {
      setLoadingAreas(false)
    }
  }

  const loadMetroStations = async () => {
    try {
      setLoadingMetro(true)
      const response = await api.get('/api/metro', { params: { city_id: '1002' } }) // Минск
      setMetroStations(response.data)
    } catch (error) {
      console.error('Error loading metro stations:', error)
    } finally {
      setLoadingMetro(false)
    }
  }

  const loadVacancies = async () => {
    try {
      setLoading(true)
      const params: any = { 
        page, 
        per_page: 20, 
        sort_by: appliedFilters.sort_by, 
        sort_order: appliedFilters.sort_order 
      }
      if (searchText) {
        params.text = searchText
      }
      if (appliedFilters.area_id) params.area_id = appliedFilters.area_id
      if (appliedFilters.salary_from) params.salary_from = parseInt(appliedFilters.salary_from)
      if (appliedFilters.salary_currency) params.salary_currency = appliedFilters.salary_currency
      // Отправляем список metro_ids
      if (appliedFilters.metro_ids && appliedFilters.metro_ids.length > 0) {
        // FastAPI ожидает массив как повторяющиеся параметры: ?metro_id=1&metro_id=2
        // Axios автоматически преобразует массив в такой формат
        // Но нужно убедиться, что это массив чисел
        params.metro_id = appliedFilters.metro_ids.map(id => Number(id))
        console.log('🔍 Sending metro_ids:', params.metro_id)
      }
      if (appliedFilters.experience_id) params.experience_id = appliedFilters.experience_id
      if (appliedFilters.employment_id) params.employment_id = appliedFilters.employment_id
      if (appliedFilters.schedule_id) params.schedule_id = appliedFilters.schedule_id
      // Для отладки - логируем полный URL
      console.log('🔍 Full request params:', params)
      console.log('🔍 metro_id in params:', params.metro_id)
      
      const response = await api.get('/api/vacancies', { 
        params,
        paramsSerializer: {
          indexes: null // Это заставит Axios использовать формат ?metro_id=5&metro_id=3
        }
      })
      setVacancies(response.data)
    } catch (error) {
      console.error('Error loading vacancies:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (key: string, value: string) => {
    setTempFilters((prev: any) => ({ ...prev, [key]: value }))
  }

  const handleMetroToggle = (metroId: number) => {
    setTempFilters((prev: any) => {
      const metroIds = prev.metro_ids || []
      const newMetroIds = metroIds.includes(metroId)
        ? metroIds.filter((id: number) => id !== metroId)
        : [...metroIds, metroId]
      return { ...prev, metro_ids: newMetroIds }
    })
  }

  const applyFilters = () => {
    setAppliedFilters(tempFilters)
    localStorage.setItem('vacancyFilters', JSON.stringify(tempFilters))
    setPage(1) // Сбрасываем на первую страницу
  }

  const clearFilters = () => {
    const emptyFilters = {
      area_id: '',
      salary_from: '',
      salary_currency: '',
      metro_ids: [],
      experience_id: '',
      employment_id: '',
      schedule_id: '',
      sort_by: 'published_at',
      sort_order: 'desc'
    }
    setTempFilters(emptyFilters)
    setAppliedFilters(emptyFilters)
    localStorage.setItem('vacancyFilters', JSON.stringify(emptyFilters))
    setPage(1)
  }

  return (
    <div className="px-4 py-8">
      <div className="mb-6 flex flex-col gap-4">
        <div className="flex gap-4 items-center">
          <input
            type="text"
            placeholder="Поиск вакансий..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className={`flex-1 max-w-md px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors ${
              isDark 
                ? 'border-gray-600 bg-gray-700/50 text-white placeholder-gray-400' 
                : 'border-gray-300 text-gray-900'
            }`}
          />
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 py-2 border rounded-lg transition-colors ${
              isDark 
                ? 'border-gray-600 bg-gray-800 text-gray-300 hover:bg-gray-700' 
                : 'border-gray-300 hover:bg-gray-50'
            }`}
          >
            {showFilters ? 'Скрыть фильтры' : 'Фильтры'}
          </button>
        </div>

        {showFilters && (
          <div className={`p-4 rounded-lg border ${
            isDark ? 'bg-gray-800/50 border-gray-700' : 'bg-gray-50 border-gray-200'
          }`}>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className={`block text-sm font-medium mb-1 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>Локация</label>
                <select
                  value={tempFilters.area_id}
                  onChange={(e) => handleFilterChange('area_id', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg transition-colors ${
                    isDark 
                      ? 'border-gray-600 bg-gray-700/50 text-white' 
                      : 'border-gray-300'
                  }`}
                  disabled={loadingAreas}
                >
                  <option value="">Все регионы</option>
                  {areas.map((area) => (
                    <option key={area.id} value={area.id}>{area.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>Опыт работы</label>
                <select
                  value={tempFilters.experience_id}
                  onChange={(e) => handleFilterChange('experience_id', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg transition-colors ${
                    isDark 
                      ? 'border-gray-600 bg-gray-700/50 text-white' 
                      : 'border-gray-300'
                  }`}
                >
                  <option value="">Любой</option>
                  <option value="noExperience">Нет опыта</option>
                  <option value="between1And3">От 1 года до 3 лет</option>
                  <option value="between3And6">От 3 до 6 лет</option>
                  <option value="moreThan6">Более 6 лет</option>
                </select>
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>Тип занятости</label>
                <select
                  value={tempFilters.employment_id}
                  onChange={(e) => handleFilterChange('employment_id', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg transition-colors ${
                    isDark 
                      ? 'border-gray-600 bg-gray-700/50 text-white' 
                      : 'border-gray-300'
                  }`}
                >
                  <option value="">Любой</option>
                  <option value="full">Полная занятость</option>
                  <option value="part">Частичная занятость</option>
                  <option value="project">Проектная работа</option>
                  <option value="probation">Стажировка</option>
                </select>
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>Сортировка</label>
                <select
                  value={`${tempFilters.sort_by}_${tempFilters.sort_order}`}
                  onChange={(e) => {
                    const value = e.target.value
                    // Разделяем по последнему подчеркиванию
                    const lastUnderscoreIndex = value.lastIndexOf('_')
                    const sort_by = value.substring(0, lastUnderscoreIndex)
                    const sort_order = value.substring(lastUnderscoreIndex + 1)
                    setTempFilters((prev: any) => ({ ...prev, sort_by, sort_order }))
                  }}
                  className={`w-full px-3 py-2 border rounded-lg transition-colors ${
                    isDark 
                      ? 'border-gray-600 bg-gray-700/50 text-white' 
                      : 'border-gray-300'
                  }`}
                >
                  <option value="published_at_desc">По дате (новые)</option>
                  <option value="published_at_asc">По дате (старые)</option>
                  <option value="salary_from_desc">По зарплате (высокая)</option>
                  <option value="salary_from_asc">По зарплате (низкая)</option>
                </select>
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>Зарплата от</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    placeholder="0"
                    value={tempFilters.salary_from}
                    onChange={(e) => handleFilterChange('salary_from', e.target.value)}
                    className={`flex-1 px-3 py-2 border rounded-lg transition-colors ${
                      isDark 
                        ? 'border-gray-600 bg-gray-700/50 text-white' 
                        : 'border-gray-300'
                    }`}
                  />
                  <select
                    value={tempFilters.salary_currency}
                    onChange={(e) => handleFilterChange('salary_currency', e.target.value)}
                    className={`px-3 py-2 border rounded-lg transition-colors min-w-[80px] ${
                      isDark 
                        ? 'border-gray-600 bg-gray-700/50 text-white' 
                        : 'border-gray-300'
                    }`}
                  >
                    <option value="">Валюта</option>
                    <option value="BYN">BYN</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="RUR">RUR</option>
                  </select>
                </div>
              </div>
              <div className="md:col-span-2 lg:col-span-1">
                <label className={`block text-sm font-medium mb-1 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>Метро</label>
                <div className="relative metro-dropdown-container">
                  <button
                    type="button"
                    onClick={() => setShowMetroDropdown(!showMetroDropdown)}
                    className={`w-full px-3 py-2 border rounded-lg transition-colors text-left flex items-center justify-between ${
                      isDark 
                        ? 'border-gray-600 bg-gray-700/50 text-white' 
                        : 'border-gray-300 bg-white'
                    }`}
                    disabled={loadingMetro}
                  >
                    <span>
                      {tempFilters.metro_ids && tempFilters.metro_ids.length > 0
                        ? `Выбрано: ${tempFilters.metro_ids.length}`
                        : 'Выберите станции'}
                    </span>
                    <span className="ml-2">▼</span>
                  </button>
                  {showMetroDropdown && (
                    <div className={`absolute z-10 w-full mt-1 border rounded-lg shadow-lg ${
                      isDark 
                        ? 'border-gray-600 bg-gray-800' 
                        : 'border-gray-300 bg-white'
                    }`}>
                      <div className={`max-h-48 overflow-y-auto p-2 ${
                        isDark ? 'bg-gray-800' : 'bg-white'
                      }`}>
                        {loadingMetro ? (
                          <div className={`text-sm p-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                            Загрузка...
                          </div>
                        ) : metroStations.length === 0 ? (
                          <div className={`text-sm p-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                            Нет станций
                          </div>
                        ) : (
                          <div className="space-y-1">
                            {metroStations.map((station) => (
                              <label
                                key={station.id}
                                className={`flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity p-1 rounded ${
                                  isDark 
                                    ? 'text-gray-300 hover:bg-gray-700' 
                                    : 'text-gray-700 hover:bg-gray-100'
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={(tempFilters.metro_ids || []).includes(station.id)}
                                  onChange={() => handleMetroToggle(station.id)}
                                  className={`w-4 h-4 rounded ${
                                    isDark 
                                      ? 'bg-gray-600 border-gray-500 text-blue-500' 
                                      : 'border-gray-300 text-blue-600'
                                  }`}
                                />
                                <span className="text-sm">{station.name}</span>
                              </label>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <button
                onClick={applyFilters}
                className={`px-6 py-2 rounded-lg transition-colors ${
                  isDark 
                    ? 'bg-blue-600 text-white hover:bg-blue-700' 
                    : 'bg-blue-500 text-white hover:bg-blue-600'
                }`}
              >
                Применить фильтры
              </button>
              <button
                onClick={clearFilters}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  isDark 
                    ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' 
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Сбросить фильтры
              </button>
            </div>
          </div>
        )}
      </div>

      {loading ? (
        <div className={`text-center py-12 transition-colors ${
          isDark ? 'text-gray-300' : 'text-gray-600'
        }`}>Загрузка...</div>
      ) : vacancies && vacancies.items.length > 0 ? (
        <>
          <div className="space-y-4">
            {vacancies.items.map((vacancy) => (
              <VacancyCard key={vacancy.id} vacancy={vacancy} />
            ))}
          </div>
          <div className="mt-6 flex justify-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className={`px-4 py-2 border rounded-lg disabled:opacity-50 transition-colors ${
                isDark 
                  ? 'border-gray-600 bg-gray-800 text-gray-300 hover:bg-gray-700' 
                  : 'border-gray-300 hover:bg-gray-50'
              }`}
            >
              Назад
            </button>
            <span className={`px-4 py-2 transition-colors ${
              isDark ? 'text-gray-300' : 'text-gray-700'
            }`}>
              Страница {page} из {Math.ceil((vacancies?.total || 0) / 20)}
            </span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page >= Math.ceil((vacancies?.total || 0) / 20)}
              className={`px-4 py-2 border rounded-lg disabled:opacity-50 transition-colors ${
                isDark 
                  ? 'border-gray-600 bg-gray-800 text-gray-300 hover:bg-gray-700' 
                  : 'border-gray-300 hover:bg-gray-50'
              }`}
            >
              Вперед
            </button>
          </div>
        </>
      ) : (
        <div className={`text-center py-12 transition-colors ${
          isDark ? 'text-gray-400' : 'text-gray-500'
        }`}>
          Вакансии не найдены
        </div>
      )}
    </div>
  )
}
