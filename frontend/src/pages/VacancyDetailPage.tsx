import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import api from '../services/api'
import { Vacancy } from '../types'

export default function VacancyDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const [vacancy, setVacancy] = useState<Vacancy | null>(null)
  const [loading, setLoading] = useState(true)
  const [isFavorite, setIsFavorite] = useState(false)
  const token = localStorage.getItem('access_token')

  useEffect(() => {
    loadVacancy()
    if (token) {
      checkFavorite()
    }
  }, [id, token])

  const loadVacancy = async () => {
    try {
      const response = await api.get(`/api/vacancies/${id}`)
      setVacancy(response.data)
    } catch (error) {
      console.error('Error loading vacancy:', error)
    } finally {
      setLoading(false)
    }
  }

  const checkFavorite = async () => {
    try {
      const response = await api.get('/api/favorites')
      const favorites = response.data
      setIsFavorite(favorites.some((fav: Vacancy) => fav.id === parseInt(id || '0')))
    } catch (error) {
      console.error('Error checking favorite:', error)
    }
  }

  const toggleFavorite = async () => {
    if (!token) {
      navigate('/login')
      return
    }

    try {
      if (isFavorite) {
        await api.delete(`/api/favorites/${id}`)
        setIsFavorite(false)
      } else {
        await api.post(`/api/favorites/${id}`)
        setIsFavorite(true)
      }
    } catch (error) {
      console.error('Error toggling favorite:', error)
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

  if (loading) {
    return (
      <div className={`text-center py-12 transition-colors ${
        isDark ? 'text-gray-300' : 'text-gray-600'
      }`}>Загрузка...</div>
    )
  }

  if (!vacancy) {
    return (
      <div className={`text-center py-12 transition-colors ${
        isDark ? 'text-gray-300' : 'text-gray-600'
      }`}>Вакансия не найдена</div>
    )
  }

  return (
    <div className="px-4 py-8 max-w-4xl mx-auto">
      <div className={`rounded-lg shadow-sm p-6 transition-colors ${
        isDark 
          ? 'bg-gray-800/50 border border-gray-700' 
          : 'bg-white'
      }`}>
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className={`text-3xl font-bold mb-2 transition-colors ${
              isDark ? 'text-white' : 'text-gray-900'
            }`}>{vacancy.name}</h1>
            <p className={`text-xl transition-colors ${
              isDark ? 'text-gray-300' : 'text-gray-600'
            }`}>{vacancy.employer_name}</p>
          </div>
          {token && (
            <button
              onClick={toggleFavorite}
              className={`px-4 py-2 rounded-lg transition-colors ${
                isFavorite
                  ? isDark
                    ? 'bg-yellow-600 text-yellow-100 hover:bg-yellow-700'
                    : 'bg-yellow-400 text-yellow-900 hover:bg-yellow-500'
                  : isDark
                    ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {isFavorite ? '★ В избранном' : '☆ В избранное'}
            </button>
          )}
        </div>

        <div className="mb-6">
          <p className={`mb-2 transition-colors ${
            isDark ? 'text-gray-300' : 'text-gray-600'
          }`}>
            {vacancy.area_name} {vacancy.address_city && `• ${vacancy.address_city}`}
          </p>
          <div className="flex flex-wrap gap-2 mb-4">
            {vacancy.salary_from && (
              <span className={`text-2xl font-bold transition-colors ${
                isDark ? 'text-white' : 'text-gray-900'
              }`}>
                {formatSalary(vacancy.salary_from, vacancy.salary_to, vacancy.salary_currency)}
              </span>
            )}
            {vacancy.experience_name && (
              <span className={`px-3 py-1 rounded transition-colors ${
                isDark
                  ? 'bg-blue-900/50 text-blue-300'
                  : 'bg-blue-100 text-blue-800'
              }`}>
                {vacancy.experience_name}
              </span>
            )}
            {vacancy.employment_name && (
              <span className={`px-3 py-1 rounded transition-colors ${
                isDark
                  ? 'bg-green-900/50 text-green-300'
                  : 'bg-green-100 text-green-800'
              }`}>
                {vacancy.employment_name}
              </span>
            )}
            {vacancy.work_format_name && (
              <span className={`px-3 py-1 rounded transition-colors ${
                isDark
                  ? 'bg-purple-900/50 text-purple-300'
                  : 'bg-purple-100 text-purple-800'
              }`}>
                {vacancy.work_format_name}
              </span>
            )}
          </div>
        </div>

        {vacancy.description && (
          <div className="mb-6">
            <h2 className={`text-xl font-semibold mb-3 transition-colors ${
              isDark ? 'text-white' : 'text-gray-900'
            }`}>Описание</h2>
            <div
              className={`prose max-w-none ${
                isDark 
                  ? 'prose-invert prose-headings:text-white prose-p:text-gray-300 prose-strong:text-white' 
                  : ''
              }`}
              dangerouslySetInnerHTML={{ __html: vacancy.description }}
            />
          </div>
        )}

        {vacancy.snippet_requirement && (
          <div className="mb-6">
            <h2 className={`text-xl font-semibold mb-3 transition-colors ${
              isDark ? 'text-white' : 'text-gray-900'
            }`}>Требования</h2>
            <p className={`transition-colors ${
              isDark ? 'text-gray-300' : 'text-gray-700'
            }`}>{vacancy.snippet_requirement}</p>
          </div>
        )}

        {vacancy.snippet_responsibility && (
          <div className="mb-6">
            <h2 className={`text-xl font-semibold mb-3 transition-colors ${
              isDark ? 'text-white' : 'text-gray-900'
            }`}>Обязанности</h2>
            <p className={`transition-colors ${
              isDark ? 'text-gray-300' : 'text-gray-700'
            }`}>{vacancy.snippet_responsibility}</p>
          </div>
        )}

        {vacancy.alternate_url && (
          <a
            href={vacancy.alternate_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 transition-colors"
          >
            Открыть на HeadHunter
          </a>
        )}
      </div>
    </div>
  )
}

