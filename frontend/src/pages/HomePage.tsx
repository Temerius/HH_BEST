import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import api from '../services/api'
import { User } from '../types'

export default function HomePage() {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      loadUser()
    } else {
      setLoading(false)
    }
  }, [])

  const loadUser = async () => {
    try {
      const response = await api.get('/api/users/me')
      setUser(response.data)
    } catch (error) {
      console.error('Error loading user:', error)
    } finally {
      setLoading(false)
    }
  }

  const getAvatarUrl = () => {
    if (user?.avatar_url) {
      // Если это полный URL (OAuth), используем его
      if (user.avatar_url.startsWith('http')) {
        return user.avatar_url
      }
      // Если относительный путь, добавляем базовый URL
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      return `${baseUrl}${user.avatar_url}`
    }
    // Аватарка по умолчанию
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    return `${baseUrl}/api/users/avatar/ava.png`
  }

  return (
    <div className="px-4 py-8">
      <div className="text-center">
        {user && (
          <div className="flex justify-center mb-6">
            <div className="relative">
              <img
                src={getAvatarUrl()}
                alt={user.first_name || user.email}
                className="w-24 h-24 rounded-full object-cover border-4 border-blue-500 dark:border-blue-400 shadow-lg"
                onError={(e) => {
                  // Если загрузка не удалась, используем аватарку по умолчанию
                  const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
                  e.currentTarget.src = `${baseUrl}/api/users/avatar/ava.png`
                }}
              />
            </div>
          </div>
        )}
        <h1 className={`text-4xl font-bold mb-4 transition-colors ${
          isDark ? 'text-white' : 'text-gray-900'
        }`}>
          Найди работу мечты
        </h1>
        <p className={`text-xl mb-8 transition-colors ${
          isDark ? 'text-gray-300' : 'text-gray-600'
        }`}>
          Платформа поиска работы с ИИ-помощником для составления резюме
        </p>
        <Link
          to="/vacancies"
          className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg text-lg font-medium hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 transition-colors"
        >
          Найти вакансии
        </Link>
      </div>
    </div>
  )
}

