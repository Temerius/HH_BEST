import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import api from '../services/api'
import { User, Resume } from '../types'

export default function ProfilePage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const [user, setUser] = useState<User | null>(null)
  const [resumes, setResumes] = useState<Resume[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      navigate('/login')
      return
    }
    loadProfile()
  }, [])

  const loadProfile = async () => {
    try {
      const [userResponse, resumesResponse] = await Promise.all([
        api.get('/api/users/me'),
        api.get('/api/resumes')
      ])
      setUser(userResponse.data)
      setResumes(resumesResponse.data)
    } catch (error) {
      console.error('Error loading profile:', error)
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

  const getAvatarUrl = () => {
    if (user?.avatar_url) {
      if (user.avatar_url.startsWith('http')) {
        return user.avatar_url
      }
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      return `${baseUrl}${user.avatar_url}`
    }
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    return `${baseUrl}/api/users/avatar/ava.png`
  }

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      alert('Пожалуйста, выберите изображение')
      return
    }

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await api.post('/api/users/me/avatar', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      setUser(response.data)
    } catch (error) {
      console.error('Error uploading avatar:', error)
      alert('Ошибка при загрузке аватарки')
    }
  }

  return (
    <div className="px-4 py-8">
      <h1 className={`text-3xl font-bold mb-6 transition-colors ${
        isDark ? 'text-white' : 'text-gray-900'
      }`}>Профиль</h1>
      {user && (
        <div className={`rounded-lg shadow-sm p-6 mb-6 transition-colors ${
          isDark 
            ? 'bg-gray-800/50 border border-gray-700' 
            : 'bg-white'
        }`}>
          <div className="flex items-center mb-6">
            <div className="relative mr-6">
              <img
                src={getAvatarUrl()}
                alt={user.first_name || user.email}
                className="w-24 h-24 rounded-full object-cover border-4 border-blue-500 dark:border-blue-400 shadow-lg"
                onError={(e) => {
                  const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
                  e.currentTarget.src = `${baseUrl}/api/users/avatar/ava.png`
                }}
              />
              <label
                htmlFor="avatar-upload"
                className="absolute bottom-0 right-0 bg-blue-600 dark:bg-blue-500 text-white rounded-full p-2 cursor-pointer hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors shadow-lg"
                title="Загрузить аватарку"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </label>
              <input
                id="avatar-upload"
                type="file"
                accept="image/*"
                onChange={handleAvatarUpload}
                className="hidden"
              />
            </div>
            <div>
              <h2 className={`text-xl font-semibold transition-colors ${
                isDark ? 'text-white' : 'text-gray-900'
              }`}>
                {user.first_name && user.last_name 
                  ? `${user.first_name} ${user.last_name}`
                  : user.first_name || user.email}
              </h2>
              <p className={`text-sm transition-colors ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>{user.email}</p>
            </div>
          </div>
          <h2 className={`text-xl font-semibold mb-4 transition-colors ${
            isDark ? 'text-white' : 'text-gray-900'
          }`}>Личная информация</h2>
          <div className="space-y-2">
            <p className={isDark ? 'text-gray-300' : 'text-gray-700'}>
              <strong className={isDark ? 'text-white' : 'text-gray-900'}>Email:</strong> {user.email}
            </p>
            {user.first_name && (
              <p className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                <strong className={isDark ? 'text-white' : 'text-gray-900'}>Имя:</strong> {user.first_name}
              </p>
            )}
            {user.last_name && (
              <p className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                <strong className={isDark ? 'text-white' : 'text-gray-900'}>Фамилия:</strong> {user.last_name}
              </p>
            )}
            {user.phone && (
              <p className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                <strong className={isDark ? 'text-white' : 'text-gray-900'}>Телефон:</strong> {user.phone}
              </p>
            )}
          </div>
        </div>
      )}

      <div className={`rounded-lg shadow-sm p-6 transition-colors ${
        isDark 
          ? 'bg-gray-800/50 border border-gray-700' 
          : 'bg-white'
      }`}>
        <h2 className={`text-xl font-semibold mb-4 transition-colors ${
          isDark ? 'text-white' : 'text-gray-900'
        }`}>Резюме</h2>
        {resumes.length > 0 ? (
          <div className="space-y-4">
            {resumes.map((resume) => (
              <div 
                key={resume.id} 
                className={`border rounded-lg p-4 transition-colors ${
                  isDark 
                    ? 'border-gray-700 bg-gray-700/30' 
                    : 'border-gray-200'
                }`}
              >
                <h3 className={`text-lg font-semibold transition-colors ${
                  isDark ? 'text-white' : 'text-gray-900'
                }`}>{resume.title}</h3>
                {resume.position && (
                  <p className={`transition-colors ${
                    isDark ? 'text-gray-300' : 'text-gray-600'
                  }`}>{resume.position}</p>
                )}
                {resume.is_primary && (
                  <span className={`inline-block mt-2 px-2 py-1 rounded text-sm transition-colors ${
                    isDark
                      ? 'bg-blue-900/50 text-blue-300'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    Основное
                  </span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className={`transition-colors ${
            isDark ? 'text-gray-400' : 'text-gray-500'
          }`}>У вас пока нет резюме</p>
        )}
      </div>
    </div>
  )
}

