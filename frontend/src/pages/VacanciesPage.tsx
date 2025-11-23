import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import api from '../services/api'
import { VacancyListResponse } from '../types'

export default function VacanciesPage() {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const [vacancies, setVacancies] = useState<VacancyListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [searchText, setSearchText] = useState('')

  useEffect(() => {
    loadVacancies()
  }, [page, searchText])

  const loadVacancies = async () => {
    try {
      setLoading(true)
      const params: any = { page, per_page: 20 }
      if (searchText) {
        params.text = searchText
      }
      const response = await api.get('/api/vacancies', { params })
      setVacancies(response.data)
    } catch (error) {
      console.error('Error loading vacancies:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatSalary = (from?: number, to?: number, currency?: string) => {
    if (!from && !to) return 'Не указана'
    const currencySymbol = currency === 'RUR' ? '₽' : currency
    if (from && to) return `${from.toLocaleString()} - ${to.toLocaleString()} ${currencySymbol}`
    if (from) return `от ${from.toLocaleString()} ${currencySymbol}`
    if (to) return `до ${to.toLocaleString()} ${currencySymbol}`
    return 'Не указана'
  }

  return (
    <div className="px-4 py-8">
      <div className="mb-6">
        <input
          type="text"
          placeholder="Поиск вакансий..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          className={`w-full max-w-md px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors ${
            isDark 
              ? 'border-gray-600 bg-gray-700/50 text-white placeholder-gray-400' 
              : 'border-gray-300 text-gray-900'
          }`}
        />
      </div>

      {loading ? (
        <div className={`text-center py-12 transition-colors ${
          isDark ? 'text-gray-300' : 'text-gray-600'
        }`}>Загрузка...</div>
      ) : vacancies && vacancies.items.length > 0 ? (
        <>
          <div className="space-y-4">
            {vacancies.items.map((vacancy) => (
              <Link
                key={vacancy.id}
                to={`/vacancies/${vacancy.id}`}
                className={`block rounded-lg shadow-sm hover:shadow-md transition-all p-6 ${
                  isDark 
                    ? 'bg-gray-800/50 border border-gray-700 hover:border-gray-600' 
                    : 'bg-white'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className={`text-xl font-semibold mb-2 transition-colors ${
                      isDark ? 'text-white' : 'text-gray-900'
                    }`}>
                      {vacancy.name}
                    </h3>
                    <p className={`mb-2 transition-colors ${
                      isDark ? 'text-gray-300' : 'text-gray-600'
                    }`}>{vacancy.employer_name}</p>
                    <p className={`text-sm mb-2 transition-colors ${
                      isDark ? 'text-gray-400' : 'text-gray-500'
                    }`}>
                      {vacancy.area_name} {vacancy.address_city && `• ${vacancy.address_city}`}
                    </p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {vacancy.salary_from && (
                        <span className={`text-lg font-semibold transition-colors ${
                          isDark ? 'text-white' : 'text-gray-900'
                        }`}>
                          {formatSalary(vacancy.salary_from, vacancy.salary_to, vacancy.salary_currency)}
                        </span>
                      )}
                      {vacancy.experience_name && (
                        <span className={`px-2 py-1 rounded text-sm transition-colors ${
                          isDark 
                            ? 'bg-gray-700 text-gray-300' 
                            : 'bg-gray-100 text-gray-700'
                        }`}>
                          {vacancy.experience_name}
                        </span>
                      )}
                      {vacancy.work_format_name && (
                        <span className={`px-2 py-1 rounded text-sm transition-colors ${
                          isDark 
                            ? 'bg-gray-700 text-gray-300' 
                            : 'bg-gray-100 text-gray-700'
                        }`}>
                          {vacancy.work_format_name}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </Link>
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

