import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import api from '../services/api'
import { Vacancy } from '../types'
import VacancyCard from '../components/VacancyCard'

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
            <VacancyCard key={vacancy.id} vacancy={vacancy} />
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

