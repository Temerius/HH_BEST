import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import api from '../services/api'
import { Vacancy } from '../types'

export default function FavoritesPage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      navigate('/login')
      return
    }
    loadFavorites()
  }, [])

  const loadFavorites = async () => {
    try {
      const response = await api.get('/api/favorites')
      setVacancies(response.data)
    } catch (error) {
      console.error('Error loading favorites:', error)
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

  if (loading) {
    return (
      <div className={`text-center py-12 transition-colors ${
        isDark ? 'text-gray-300' : 'text-gray-600'
      }`}>Загрузка...</div>
    )
  }

  return (
    <div className="px-4 py-8">
      <h1 className={`text-3xl font-bold mb-6 transition-colors ${
        isDark ? 'text-white' : 'text-gray-900'
      }`}>Избранные вакансии</h1>
      {vacancies.length > 0 ? (
        <div className="space-y-4">
          {vacancies.map((vacancy) => (
            <Link
              key={vacancy.id}
              to={`/vacancies/${vacancy.id}`}
              className={`block rounded-lg shadow-sm hover:shadow-md transition-all p-6 ${
                isDark 
                  ? 'bg-gray-800/50 border border-gray-700 hover:border-gray-600' 
                  : 'bg-white'
              }`}
            >
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
              <div className="flex flex-wrap gap-2">
                {vacancy.salary_from && (
                  <span className={`text-lg font-semibold transition-colors ${
                    isDark ? 'text-white' : 'text-gray-900'
                  }`}>
                    {formatSalary(vacancy.salary_from, vacancy.salary_to, vacancy.salary_currency)}
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className={`text-center py-12 transition-colors ${
          isDark ? 'text-gray-400' : 'text-gray-500'
        }`}>
          У вас пока нет избранных вакансий
        </div>
      )}
    </div>
  )
}

