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

export default function VacanciesPage() {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const [vacancies, setVacancies] = useState<VacancyListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [searchText, setSearchText] = useState('')
  const [areas, setAreas] = useState<Area[]>([])
  const [loadingAreas, setLoadingAreas] = useState(false)
  
  // Временные фильтры (не применяются до нажатия кнопки)
  const [tempFilters, setTempFilters] = useState(() => {
    const saved = localStorage.getItem('vacancyFilters')
    return saved ? JSON.parse(saved) : {
      area_id: '',
      salary_from: '',
      salary_to: '',
      experience_id: '',
      employment_id: '',
      work_format_id: '',
      schedule_id: '',
      sort_by: 'published_at',
      sort_order: 'desc'
    }
  })
  
  // Примененные фильтры (используются для запросов)
  const [appliedFilters, setAppliedFilters] = useState(() => {
    const saved = localStorage.getItem('vacancyFilters')
    return saved ? JSON.parse(saved) : {
      area_id: '',
      salary_from: '',
      salary_to: '',
      experience_id: '',
      employment_id: '',
      work_format_id: '',
      schedule_id: '',
      sort_by: 'published_at',
      sort_order: 'desc'
    }
  })
  
  const [showFilters, setShowFilters] = useState(false)

  // Загружаем области при монтировании
  useEffect(() => {
    loadAreas()
  }, [])

  // Загружаем вакансии при изменении примененных фильтров или страницы
  useEffect(() => {
    loadVacancies()
  }, [page, searchText, appliedFilters])

  const loadAreas = async () => {
    try {
      setLoadingAreas(true)
      const response = await api.get('/api/areas', { params: { limit: 200 } })
      setAreas(response.data)
    } catch (error) {
      console.error('Error loading areas:', error)
    } finally {
      setLoadingAreas(false)
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
      if (appliedFilters.salary_to) params.salary_to = parseInt(appliedFilters.salary_to)
      if (appliedFilters.experience_id) params.experience_id = appliedFilters.experience_id
      if (appliedFilters.employment_id) params.employment_id = appliedFilters.employment_id
      if (appliedFilters.work_format_id) params.work_format_id = appliedFilters.work_format_id
      if (appliedFilters.schedule_id) params.schedule_id = appliedFilters.schedule_id
      const response = await api.get('/api/vacancies', { params })
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

  const applyFilters = () => {
    setAppliedFilters(tempFilters)
    localStorage.setItem('vacancyFilters', JSON.stringify(tempFilters))
    setPage(1) // Сбрасываем на первую страницу
  }

  const clearFilters = () => {
    const emptyFilters = {
      area_id: '',
      salary_from: '',
      salary_to: '',
      experience_id: '',
      employment_id: '',
      work_format_id: '',
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
                }`}>Опыт</label>
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
                  <option value="between1And3">1-3 года</option>
                  <option value="between3And6">3-6 лет</option>
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
                  <option value="volunteer">Волонтерство</option>
                  <option value="probation">Стажировка</option>
                </select>
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>Формат работы</label>
                <select
                  value={tempFilters.work_format_id}
                  onChange={(e) => handleFilterChange('work_format_id', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg transition-colors ${
                    isDark 
                      ? 'border-gray-600 bg-gray-700/50 text-white' 
                      : 'border-gray-300'
                  }`}
                >
                  <option value="">Любой</option>
                  <option value="remote">Удаленно</option>
                  <option value="hybrid">Гибрид</option>
                  <option value="fullDay">Полный день</option>
                </select>
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>Сортировка</label>
                <select
                  value={`${tempFilters.sort_by}_${tempFilters.sort_order}`}
                  onChange={(e) => {
                    const [sort_by, sort_order] = e.target.value.split('_')
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
                  <option value="name_asc">По названию (А-Я)</option>
                  <option value="name_desc">По названию (Я-А)</option>
                </select>
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>Зарплата от</label>
                <input
                  type="number"
                  placeholder="0"
                  value={tempFilters.salary_from}
                  onChange={(e) => handleFilterChange('salary_from', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg transition-colors ${
                    isDark 
                      ? 'border-gray-600 bg-gray-700/50 text-white' 
                      : 'border-gray-300'
                  }`}
                />
              </div>
              <div>
                <label className={`block text-sm font-medium mb-1 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>Зарплата до</label>
                <input
                  type="number"
                  placeholder="1000000"
                  value={tempFilters.salary_to}
                  onChange={(e) => handleFilterChange('salary_to', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg transition-colors ${
                    isDark 
                      ? 'border-gray-600 bg-gray-700/50 text-white' 
                      : 'border-gray-300'
                  }`}
                />
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
