import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import api from '../services/api'
import { User, Resume } from '../types'

export default function ProfilePage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const [user, setUser] = useState<User | null>(null)
  const [resumes, setResumes] = useState<Resume[]>([])
  const [userSkills, setUserSkills] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [uploadingResume, setUploadingResume] = useState(false)
  const [deletingResume, setDeletingResume] = useState(false)
  const [showPdfViewer, setShowPdfViewer] = useState(false)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)

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
      const [userResponse, resumesResponse, skillsResponse] = await Promise.all([
        api.get('/api/users/me'),
        api.get('/api/resumes'),
        api.get('/api/skills/my')
      ])
      setUser(userResponse.data)
      setResumes(resumesResponse.data)
      setUserSkills(skillsResponse.data)
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

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.type !== 'application/pdf') {
      alert('Пожалуйста, выберите PDF файл')
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      alert('Размер файла не должен превышать 10 МБ')
      return
    }

    try {
      setUploadingResume(true)
      const formData = new FormData()
      formData.append('file', file)

      await api.post('/api/resumes/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      // Обновляем список резюме
      await loadProfile()
    } catch (error: any) {
      console.error('Error uploading resume:', error)
      alert(error.response?.data?.detail || 'Ошибка при загрузке резюме')
    } finally {
      setUploadingResume(false)
      // Сбрасываем значение input, чтобы можно было загрузить тот же файл снова
      e.target.value = ''
    }
  }

  const handleDeleteResume = async () => {
    try {
      setDeletingResume(true)
      await api.delete('/api/resumes/file')
      await loadProfile()
    } catch (error: any) {
      console.error('Error deleting resume:', error)
      alert(error.response?.data?.detail || 'Ошибка при удалении резюме')
    } finally {
      setDeletingResume(false)
    }
  }

  const handleViewResume = async (resume: Resume) => {
    if (!resume.file_path) return
    
    try {
      // Загружаем PDF через API с авторизацией
      // file_path содержит путь вида /api/resumes/file
      const url = resume.file_path.startsWith('http') 
        ? resume.file_path.replace(/^https?:\/\/[^\/]+/, '') // Убираем домен, оставляем только путь
        : resume.file_path
      
      // Используем api сервис, который уже настроен с авторизацией
      const response = await api.get(url, {
        responseType: 'blob'
      })
      
      // Создаем blob из ответа
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const blobUrl = URL.createObjectURL(blob)
      
      setPdfUrl(blobUrl)
      setShowPdfViewer(true)
    } catch (error: any) {
      console.error('Error loading resume:', error)
      alert(error.response?.data?.detail || 'Ошибка при загрузке резюме')
    }
  }

  const getResumeWithFile = () => {
    return resumes.find(r => r.file_path)
  }

  return (
    <div className="px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className={`text-3xl font-bold transition-colors ${
          isDark ? 'text-white' : 'text-gray-900'
        }`}>Профиль</h1>
        <Link
          to="/profile/edit"
          className={`px-4 py-2 rounded-lg transition-colors ${
            isDark
              ? 'bg-blue-600 hover:bg-blue-700 text-white'
              : 'bg-blue-500 hover:bg-blue-600 text-white'
          }`}
        >
          Редактировать
        </Link>
      </div>
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
              {user.specialization && (
                <p className={`text-sm transition-colors ${
                  isDark ? 'text-blue-400' : 'text-blue-600'
                }`}>
                  {user.specialization}
                </p>
              )}
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
            {user.specialization && (
              <p className={isDark ? 'text-gray-300' : 'text-gray-700'}>
                <strong className={isDark ? 'text-white' : 'text-gray-900'}>Направление:</strong> {user.specialization}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Навыки */}
      {userSkills.length > 0 && (
        <div className={`rounded-lg shadow-sm p-6 mb-6 transition-colors ${
          isDark 
            ? 'bg-gray-800/50 border border-gray-700' 
            : 'bg-white'
        }`}>
          <h2 className={`text-xl font-semibold mb-4 transition-colors ${
            isDark ? 'text-white' : 'text-gray-900'
          }`}>Навыки</h2>
          <div className="flex flex-wrap gap-2">
            {userSkills.map((skill) => (
              <span
                key={skill.skill_id}
                className={`px-3 py-1 rounded-full text-sm transition-colors ${
                  isDark
                    ? 'bg-blue-900/50 text-blue-300 border border-blue-700'
                    : 'bg-blue-100 text-blue-800 border border-blue-200'
                }`}
              >
                {skill.skill_name}
                {skill.level && (
                  <span className="ml-1 text-xs opacity-75">
                    ({skill.level})
                  </span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className={`rounded-lg shadow-sm p-6 transition-colors ${
        isDark 
          ? 'bg-gray-800/50 border border-gray-700' 
          : 'bg-white'
      }`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className={`text-xl font-semibold transition-colors ${
            isDark ? 'text-white' : 'text-gray-900'
          }`}>Резюме (PDF)</h2>
          <div className="flex gap-2">
            {getResumeWithFile() && (
              <button
                onClick={handleDeleteResume}
                disabled={deletingResume}
                className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                  isDark
                    ? 'bg-red-600 hover:bg-red-700 text-white'
                    : 'bg-red-500 hover:bg-red-600 text-white'
                } disabled:opacity-50`}
              >
                {deletingResume ? 'Удаление...' : 'Удалить'}
              </button>
            )}
            <label
              htmlFor="resume-upload"
              className={`px-4 py-2 rounded-lg text-sm cursor-pointer transition-colors ${
                isDark
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              } ${uploadingResume ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {uploadingResume ? 'Загрузка...' : getResumeWithFile() ? 'Заменить резюме' : 'Загрузить резюме'}
            </label>
            <input
              id="resume-upload"
              type="file"
              accept="application/pdf"
              onChange={handleResumeUpload}
              disabled={uploadingResume}
              className="hidden"
            />
          </div>
        </div>
        
        {getResumeWithFile() ? (
          <div className={`border rounded-lg p-4 transition-colors ${
            isDark 
              ? 'border-gray-700 bg-gray-700/30' 
              : 'border-gray-200'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <svg className={`w-8 h-8 ${isDark ? 'text-red-400' : 'text-red-500'}`} fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                </svg>
                <div>
                  <h3 className={`text-lg font-semibold transition-colors ${
                    isDark ? 'text-white' : 'text-gray-900'
                  }`}>Резюме.pdf</h3>
                  <p className={`text-sm transition-colors ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>PDF документ</p>
                </div>
              </div>
              <button
                onClick={() => handleViewResume(getResumeWithFile()!)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  isDark
                    ? 'bg-green-600 hover:bg-green-700 text-white'
                    : 'bg-green-500 hover:bg-green-600 text-white'
                }`}
              >
                Открыть
              </button>
            </div>
          </div>
        ) : (
          <div className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            isDark 
              ? 'border-gray-600 bg-gray-800/30' 
              : 'border-gray-300 bg-gray-50'
          }`}>
            <svg className={`w-16 h-16 mx-auto mb-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            <p className={`mb-2 transition-colors ${
              isDark ? 'text-gray-400' : 'text-gray-500'
            }`}>У вас пока нет загруженного резюме</p>
            <p className={`text-sm transition-colors ${
              isDark ? 'text-gray-500' : 'text-gray-400'
            }`}>Загрузите PDF файл вашего резюме</p>
          </div>
        )}
      </div>

      {/* Модальное окно для просмотра PDF */}
      {showPdfViewer && pdfUrl && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75"
          onClick={() => {
            setShowPdfViewer(false)
            // Освобождаем память от blob URL
            if (pdfUrl.startsWith('blob:')) {
              URL.revokeObjectURL(pdfUrl)
            }
            setPdfUrl(null)
          }}
        >
          <div 
            className={`relative w-full h-full max-w-5xl max-h-[90vh] m-4 ${isDark ? 'bg-gray-900' : 'bg-white'} rounded-lg shadow-2xl`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                Резюме
              </h3>
              <button
                onClick={() => {
                  setShowPdfViewer(false)
                  // Освобождаем память от blob URL
                  if (pdfUrl.startsWith('blob:')) {
                    URL.revokeObjectURL(pdfUrl)
                  }
                  setPdfUrl(null)
                }}
                className={`p-2 rounded-lg transition-colors ${
                  isDark
                    ? 'hover:bg-gray-700 text-gray-300'
                    : 'hover:bg-gray-100 text-gray-600'
                }`}
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="h-[calc(90vh-80px)] overflow-auto">
              <iframe
                src={pdfUrl}
                className="w-full h-full"
                title="Резюме PDF"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

