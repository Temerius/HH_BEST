import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import { Vacancy } from '../types'
import api from '../services/api'

interface VacancyCardProps {
  vacancy: Vacancy
}

export default function VacancyCard({ vacancy }: VacancyCardProps) {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const navigate = useNavigate()
  const [isFavorite, setIsFavorite] = useState(false)
  const token = localStorage.getItem('access_token')

  useEffect(() => {
    if (token) {
      checkFavorite()
    }
  }, [token, vacancy.id])

  const checkFavorite = async () => {
    if (!token) {
      setIsFavorite(false)
      return
    }
    try {
      const response = await api.get('/api/favorites')
      const favorites = response.data
      setIsFavorite(favorites.some((fav: Vacancy) => fav.id === vacancy.id))
    } catch (error: any) {
      // Если ошибка 401, значит не авторизован
      if (error?.response?.status === 401) {
        setIsFavorite(false)
      }
      // Игнорируем другие ошибки при проверке избранного
    }
  }

  const toggleFavorite = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (!token) {
      navigate('/login')
      return
    }

    try {
      if (isFavorite) {
        await api.delete(`/api/favorites/${vacancy.id}`)
        setIsFavorite(false)
      } else {
        await api.post(`/api/favorites/${vacancy.id}`)
        setIsFavorite(true)
      }
    } catch (error: any) {
      console.error('Error toggling favorite:', error)
      // Если ошибка 401, перенаправляем на логин
      if (error?.response?.status === 401) {
        navigate('/login')
      }
      // Если ошибка 400 (уже в избранном), обновляем состояние
      if (error?.response?.status === 400 && !isFavorite) {
        setIsFavorite(true)
      }
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
    <Link
      to={`/vacancies/${vacancy.id}`}
      className={`block rounded-lg shadow-sm hover:shadow-md transition-all p-6 ${
        isDark 
          ? 'bg-gray-800/50 border border-gray-700 hover:border-gray-600' 
          : 'bg-white'
      }`}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-start justify-between gap-2 mb-2">
            <h3 className={`text-xl font-semibold transition-colors ${
              isDark ? 'text-white' : 'text-gray-900'
            }`}>
              {vacancy.name}
            </h3>
            <button
              onClick={toggleFavorite}
              className={`text-2xl transition-colors flex-shrink-0 ${
                isFavorite
                  ? 'text-yellow-500 hover:text-yellow-600'
                  : isDark
                    ? 'text-gray-500 hover:text-yellow-500'
                    : 'text-gray-300 hover:text-yellow-500'
              }`}
              title={isFavorite ? 'Удалить из избранного' : 'Добавить в избранное'}
            >
              {isFavorite ? '★' : '☆'}
            </button>
          </div>
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
            {vacancy.employment_name && (
              <span className={`px-2 py-1 rounded text-sm transition-colors ${
                isDark 
                  ? 'bg-gray-700 text-gray-300' 
                  : 'bg-gray-100 text-gray-700'
              }`}>
                {vacancy.employment_name}
              </span>
            )}
            {vacancy.schedule_name && (
              <span className={`px-2 py-1 rounded text-sm transition-colors ${
                isDark 
                  ? 'bg-gray-700 text-gray-300' 
                  : 'bg-gray-100 text-gray-700'
              }`}>
                {vacancy.schedule_name}
              </span>
            )}
          </div>
          {vacancy.skills && vacancy.skills.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {vacancy.skills.slice(0, 5).map((skill, idx) => (
                <span
                  key={idx}
                  className={`px-2 py-1 rounded text-xs transition-colors ${
                    isDark
                      ? 'bg-blue-900/50 text-blue-300 border border-blue-700'
                      : 'bg-blue-100 text-blue-800 border border-blue-200'
                  }`}
                >
                  {skill}
                </span>
              ))}
              {vacancy.skills.length > 5 && (
                <span className={`px-2 py-1 rounded text-xs transition-colors ${
                  isDark ? 'text-gray-400' : 'text-gray-500'
                }`}>
                  +{vacancy.skills.length - 5}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </Link>
  )
}

