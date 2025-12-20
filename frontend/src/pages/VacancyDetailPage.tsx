import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import api from '../services/api'
import { Vacancy } from '../types'

// Список всех гифок (переименованы от 1 до 27)
const WAIT_GIFS = [
  '1.gif',
  '2.gif',
  '3.gif',
  '4.gif',
  '5.gif',
  '6.gif',
  '7.gif',
  '8.gif',
  '9.gif',
  '10.gif',
  '11.gif',
  '12.gif',
  '13.gif',
  '14.gif',
  '15.gif',
  '16.gif',
  '17.gif',
  '18.gif',
  '19.gif',
  '20.gif',
  '21.gif',
  '22.gif',
  '23.gif',
  '24.gif',
  '25.gif',
  '26.gif',
  '27.gif'
]

// Функция для получения случайной гифки
const getRandomGif = () => {
  const randomIndex = Math.floor(Math.random() * WAIT_GIFS.length)
  return WAIT_GIFS[randomIndex]
}

// Функция для получения URL гифки (теперь из статических файлов фронтенда)
const getGifUrl = (gifName: string) => {
  // В Vite файлы из папки public доступны по корневому пути
  return `/wait_gifs/${gifName}`
}

// Функция для парсинга markdown (жирный текст **текст**)
const parseMarkdown = (text: string): string => {
  if (!text) return ''
  // Заменяем **текст** на <strong>текст</strong>
  return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}

export default function VacancyDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const [vacancy, setVacancy] = useState<Vacancy | null>(null)
  const [loading, setLoading] = useState(true)
  const [isFavorite, setIsFavorite] = useState(false)
  const [showAIModal, setShowAIModal] = useState(false)
  const [aiMode, setAiMode] = useState<'cover-letter' | 'improve-resume' | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiResult, setAiResult] = useState<string | null>(null)
  const [currentGif, setCurrentGif] = useState<string>('')
  const [gifLoaded, setGifLoaded] = useState(false)
  const [gifError, setGifError] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)
  const gifIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const token = localStorage.getItem('access_token')

  // Эффект для смены гифки каждые 10 секунд во время загрузки
  useEffect(() => {
    if (aiLoading) {
      // Устанавливаем первую случайную гифку сразу
      const initialGif = getRandomGif()
      setCurrentGif(initialGif)
      setGifLoaded(false)
      setGifError(false)
      console.log('🎬 Setting initial GIF:', initialGif)
      
      // Меняем гифку каждые 10 секунд
      const interval = setInterval(() => {
        const newGif = getRandomGif()
        setCurrentGif(newGif)
        setGifLoaded(false)
        setGifError(false)
        console.log('🔄 Changing GIF to:', newGif)
      }, 10000)
      
      gifIntervalRef.current = interval

      return () => {
        if (gifIntervalRef.current) {
          clearInterval(gifIntervalRef.current)
          gifIntervalRef.current = null
        }
        setCurrentGif('')
        setGifLoaded(false)
        setGifError(false)
      }
    } else {
      if (gifIntervalRef.current) {
        clearInterval(gifIntervalRef.current)
        gifIntervalRef.current = null
      }
      setCurrentGif('')
      setGifLoaded(false)
      setGifError(false)
    }
  }, [aiLoading])
  
  // Функция для отмены запроса и очистки состояния
  const cancelAIRequest = () => {
    // Отменяем запрос
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    // Останавливаем смену гифок
    if (gifIntervalRef.current) {
      clearInterval(gifIntervalRef.current)
      gifIntervalRef.current = null
    }
    // Сбрасываем состояние
    setAiLoading(false)
    setAiMode(null)
    setAiResult(null)
    setCurrentGif('')
    setGifLoaded(false)
    setGifError(false)
  }

  useEffect(() => {
    loadVacancy()
    if (token) {
      checkFavorite()
    }
  }, [id, token])

  const loadVacancy = async () => {
    try {
      const response = await api.get(`/api/vacancies/${id}`)
      console.log('📥 Vacancy data received:', response.data)
      console.log('📍 URL:', response.data.url)
      console.log('📍 Coordinates:', response.data.address_lat, response.data.address_lng)
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

  const handleAIAssistant = () => {
    if (!token) {
      navigate('/login')
      return
    }
    setShowAIModal(true)
    setAiResult(null)
    setAiMode(null)
  }

  const handleGenerateCoverLetter = async () => {
    if (!vacancy) return
    
    // Отменяем предыдущий запрос, если есть
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    
    // Создаем новый AbortController
    const abortController = new AbortController()
    abortControllerRef.current = abortController
    
    setAiMode('cover-letter')
    setAiLoading(true)
    setAiResult(null)
    
    try {
      const response = await api.post('/api/ai/generate-cover-letter', {
        vacancy_id: vacancy.id,
        tone: 'professional'
      }, {
        signal: abortController.signal
      })
      
      // Проверяем, не был ли запрос отменен
      if (!abortController.signal.aborted) {
        setAiResult(response.data.cover_letter)
      }
    } catch (error: any) {
      // Игнорируем ошибку, если запрос был отменен
      if (error.code === 'ERR_CANCELED' || error.name === 'CanceledError' || error.name === 'AbortError' || abortController.signal.aborted) {
        console.log('Request cancelled')
        return
      }
      console.error('Error generating cover letter:', error)
      if (!abortController.signal.aborted) {
        alert(error.response?.data?.detail || 'Ошибка при генерации сопроводительного письма')
      }
    } finally {
      if (!abortController.signal.aborted) {
        setAiLoading(false)
        abortControllerRef.current = null
      }
    }
  }

  const handleImproveResume = async () => {
    if (!vacancy) return
    
    // Отменяем предыдущий запрос, если есть
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    
    // Создаем новый AbortController
    const abortController = new AbortController()
    abortControllerRef.current = abortController
    
    setAiMode('improve-resume')
    setAiLoading(true)
    setAiResult(null)
    
    try {
      const response = await api.post('/api/ai/improve-resume', {
        vacancy_id: vacancy.id
      }, {
        signal: abortController.signal
      })
      
      // Проверяем, не был ли запрос отменен
      if (!abortController.signal.aborted) {
        setAiResult(response.data.recommendations)
      }
    } catch (error: any) {
      // Игнорируем ошибку, если запрос был отменен
      if (error.code === 'ERR_CANCELED' || error.name === 'CanceledError' || error.name === 'AbortError' || abortController.signal.aborted) {
        console.log('Request cancelled')
        return
      }
      console.error('Error improving resume:', error)
      if (!abortController.signal.aborted) {
        alert(error.response?.data?.detail || 'Ошибка при генерации рекомендаций')
      }
    } finally {
      if (!abortController.signal.aborted) {
        setAiLoading(false)
        abortControllerRef.current = null
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
          <div className="flex items-center gap-4">
            {token && (
              <button
                onClick={handleAIAssistant}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  isDark
                    ? 'bg-purple-600 hover:bg-purple-700 text-white'
                    : 'bg-purple-500 hover:bg-purple-600 text-white'
                }`}
                title="AI Помощник"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <span>AI Помощник</span>
              </button>
            )}
            {token && (
              <button
                onClick={toggleFavorite}
                className={`text-4xl transition-colors ${
                  isFavorite
                    ? 'text-yellow-500 hover:text-yellow-600'
                    : isDark
                      ? 'text-gray-400 hover:text-yellow-500'
                      : 'text-gray-300 hover:text-yellow-500'
                }`}
                title={isFavorite ? 'Удалить из избранного' : 'Добавить в избранное'}
              >
                {isFavorite ? '★' : '☆'}
              </button>
            )}
          </div>
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


        {vacancy.skills && vacancy.skills.length > 0 && (
          <div className="mb-6">
            <h2 className={`text-xl font-semibold mb-3 transition-colors ${
              isDark ? 'text-white' : 'text-gray-900'
            }`}>Ключевые навыки</h2>
            <div className="flex flex-wrap gap-2">
              {vacancy.skills.map((skill, idx) => (
                <span
                  key={idx}
                  className={`px-3 py-1 rounded-full text-sm transition-colors ${
                    isDark
                      ? 'bg-blue-900/50 text-blue-300 border border-blue-700'
                      : 'bg-blue-100 text-blue-800 border border-blue-200'
                  }`}
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Адрес и метро */}
        {(vacancy.address_raw || vacancy.address_city || (vacancy.metro_stations && vacancy.metro_stations.length > 0)) && (
          <div className="mb-6">
            <h2 className={`text-xl font-semibold mb-3 transition-colors ${
              isDark ? 'text-white' : 'text-gray-900'
            }`}>Адрес</h2>
            <div className={`space-y-2 transition-colors ${
              isDark ? 'text-gray-300' : 'text-gray-700'
            }`}>
              {vacancy.address_raw && (
                <p className="text-base">
                  <span className="font-medium">Адрес: </span>
                  {vacancy.address_raw}
                </p>
              )}
              {!vacancy.address_raw && vacancy.address_city && (
                <p className="text-base">
                  <span className="font-medium">Город: </span>
                  {vacancy.address_city}
                </p>
              )}
              {vacancy.metro_stations && vacancy.metro_stations.length > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">Метро: </span>
                  {vacancy.metro_stations.map((station, idx) => (
                    <span
                      key={idx}
                      className={`px-3 py-1 rounded-full text-sm transition-colors ${
                        isDark
                          ? 'bg-purple-900/50 text-purple-300 border border-purple-700'
                          : 'bg-purple-100 text-purple-800 border border-purple-200'
                      }`}
                    >
                      🚇 {station.name}
                      {station.line_name && ` (${station.line_name})`}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Карта */}
        {(() => {
          // Формируем полный адрес для карты
          const addressParts = []
          if (vacancy.address_city) addressParts.push(vacancy.address_city)
          if (vacancy.address_street) addressParts.push(vacancy.address_street)
          if (vacancy.address_building) addressParts.push(vacancy.address_building)
          const fullAddress = addressParts.length > 0 
            ? addressParts.join(', ') 
            : vacancy.address_raw || ''
          
          const hasCoordinates = vacancy.address_lat != null && vacancy.address_lng != null
          const hasAddress = fullAddress.length > 0
          
          if (hasCoordinates || hasAddress) {
            return (
              <div className="mb-6">
                <h2 className={`text-xl font-semibold mb-3 transition-colors ${
                  isDark ? 'text-white' : 'text-gray-900'
                }`}>Местоположение</h2>
                <div className={`rounded-lg overflow-hidden border ${
                  isDark ? 'border-gray-700' : 'border-gray-300'
                }`} style={{ height: '400px' }}>
                  {hasCoordinates ? (
                    // Если есть координаты, используем их с красной меткой
                    <iframe
                      width="100%"
                      height="100%"
                      frameBorder="0"
                      style={{ border: 0 }}
                      src={`https://yandex.ru/map-widget/v1/?ll=${vacancy.address_lng},${vacancy.address_lat}&z=16&pt=${vacancy.address_lng},${vacancy.address_lat},pm2rdm&l=map`}
                      allowFullScreen
                      title="Местоположение вакансии"
                    />
                  ) : (
                    // Если координат нет, используем адрес для поиска с меткой
                    <iframe
                      width="100%"
                      height="100%"
                      frameBorder="0"
                      style={{ border: 0 }}
                      src={`https://yandex.ru/map-widget/v1/?text=${encodeURIComponent(fullAddress)}&z=16&pt=${encodeURIComponent(fullAddress)},pm2rdm&l=map`}
                      allowFullScreen
                      title="Местоположение вакансии"
                    />
                  )}
                </div>
                {hasCoordinates && (
                  <p className={`text-sm mt-2 transition-colors ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    Координаты: {vacancy.address_lat.toFixed(6)}, {vacancy.address_lng.toFixed(6)}
                  </p>
                )}
                {!hasCoordinates && hasAddress && (
                  <p className={`text-sm mt-2 transition-colors ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    Адрес: {fullAddress}
                  </p>
                )}
              </div>
            )
          }
          return null
        })()}

        {/* Кнопка открыть на rabota.by */}
        {vacancy.url && (
          <div className="mb-6">
            <a
              href={vacancy.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 transition-colors"
            >
              Открыть на rabota.by
            </a>
          </div>
        )}
      </div>

      {/* Модальное окно AI помощника */}
      {showAIModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75"
          onClick={() => {
            cancelAIRequest()
            setShowAIModal(false)
          }}
        >
          <div 
            className={`relative w-full h-full max-w-4xl max-h-[90vh] m-4 ${isDark ? 'bg-gray-900' : 'bg-white'} rounded-lg shadow-2xl flex flex-col`}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Заголовок */}
            <div className={`flex items-center justify-between p-6 border-b ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                🤖 AI Помощник
              </h2>
              <button
                onClick={() => {
                  cancelAIRequest()
                  setShowAIModal(false)
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

            {/* Контент */}
            <div className="flex-1 overflow-auto p-6">
              {!aiMode && !aiResult && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <button
                    onClick={handleGenerateCoverLetter}
                    className={`p-6 rounded-lg border-2 transition-all ${
                      isDark
                        ? 'border-purple-600 bg-purple-900/20 hover:bg-purple-900/40 text-white'
                        : 'border-purple-500 bg-purple-50 hover:bg-purple-100 text-gray-900'
                    }`}
                  >
                    <div className="text-4xl mb-3">✉️</div>
                    <h3 className={`text-xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      Сопроводительное письмо
                    </h3>
                    <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                      Сгенерируйте профессиональное сопроводительное письмо на основе вашего резюме и этой вакансии
                    </p>
                  </button>
                  
                  <button
                    onClick={handleImproveResume}
                    className={`p-6 rounded-lg border-2 transition-all ${
                      isDark
                        ? 'border-blue-600 bg-blue-900/20 hover:bg-blue-900/40 text-white'
                        : 'border-blue-500 bg-blue-50 hover:bg-blue-100 text-gray-900'
                    }`}
                  >
                    <div className="text-4xl mb-3">📝</div>
                    <h3 className={`text-xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      Улучшить резюме
                    </h3>
                    <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                      Получите персональные рекомендации по улучшению резюме для этой вакансии
                    </p>
                  </button>
                </div>
              )}

              {aiLoading && (
                <div className="flex flex-col items-center justify-center py-12">
                  <div 
                    className="mb-6"
                    style={{ 
                      width: '320px', 
                      height: '320px', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      backgroundColor: isDark ? 'rgba(0,0,0,0.1)' : 'rgba(0,0,0,0.05)',
                      borderRadius: '8px',
                      position: 'relative',
                      overflow: 'hidden'
                    }}
                  >
                    {currentGif ? (
                      <>
                        {!gifLoaded && !gifError && (
                          <div className={`animate-spin rounded-full h-12 w-12 border-b-2 ${isDark ? 'border-purple-500' : 'border-purple-600'} absolute`}></div>
                        )}
                        <img
                          key={`gif-${currentGif}`}
                          src={getGifUrl(currentGif)}
                          alt="Waiting..."
                          className="max-w-full max-h-full"
                          style={{ 
                            width: 'auto',
                            height: 'auto',
                            maxWidth: '400px',
                            maxHeight: '400px',
                            objectFit: 'contain',
                            visibility: gifLoaded ? 'visible' : 'hidden',
                            opacity: gifLoaded ? 1 : 0,
                            transition: 'opacity 0.3s ease-in-out'
                          }}
                          onLoad={(e) => {
                            const img = e.currentTarget
                            setGifLoaded(true)
                            setGifError(false)
                            console.log('✅ GIF loaded successfully:', currentGif)
                            console.log('🔗 URL:', getGifUrl(currentGif))
                            console.log('📐 Natural:', img.naturalWidth, 'x', img.naturalHeight)
                            console.log('📐 Displayed:', img.offsetWidth, 'x', img.offsetHeight)
                            console.log('📐 Computed display:', window.getComputedStyle(img).display)
                            console.log('📐 Computed visibility:', window.getComputedStyle(img).visibility)
                            console.log('📐 Computed opacity:', window.getComputedStyle(img).opacity)
                            console.log('📐 Parent container:', img.parentElement?.offsetWidth, 'x', img.parentElement?.offsetHeight)
                          }}
                          onError={(e) => {
                            setGifError(true)
                            setGifLoaded(false)
                            console.error('❌ Error loading GIF:', currentGif, getGifUrl(currentGif))
                            console.error('❌ Error event:', e)
                            // Если гифка не загрузилась, пробуем другую
                            setTimeout(() => {
                              const newGif = getRandomGif()
                              console.log('🔄 Trying new GIF:', newGif)
                              setCurrentGif(newGif)
                            }, 500)
                          }}
                        />
                        {gifError && (
                          <div className="text-center text-sm text-red-500 absolute inset-0 flex items-center justify-center">
                            Ошибка загрузки
                          </div>
                        )}
                      </>
                    ) : (
                      <div className={`animate-spin rounded-full h-12 w-12 border-b-2 ${isDark ? 'border-purple-500' : 'border-purple-600'}`}></div>
                    )}
                  </div>
                  <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    {aiMode === 'cover-letter' ? 'Генерирую сопроводительное письмо...' : 'Анализирую резюме...'}
                  </p>
                </div>
              )}

              {aiResult && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className={`text-xl font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {aiMode === 'cover-letter' ? '✉️ Сопроводительное письмо' : '📝 Рекомендации по улучшению резюме'}
                    </h3>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(aiResult)
                        alert('Скопировано в буфер обмена!')
                      }}
                      className={`px-4 py-2 rounded-lg transition-colors ${
                        isDark
                          ? 'bg-gray-700 hover:bg-gray-600 text-white'
                          : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                      }`}
                    >
                      Копировать
                    </button>
                  </div>
                  <div 
                    className={`prose max-w-none p-4 rounded-lg ${
                      isDark 
                        ? 'bg-gray-800 prose-invert prose-headings:text-white prose-p:text-gray-300 prose-strong:text-white' 
                        : 'bg-gray-50 prose-strong:text-gray-900'
                    }`}
                  >
                    <div 
                      className="whitespace-pre-wrap"
                      dangerouslySetInnerHTML={{ __html: parseMarkdown(aiResult) }}
                    />
                  </div>
                  <button
                    onClick={() => {
                      setAiMode(null)
                      setAiResult(null)
                    }}
                    className={`px-4 py-2 rounded-lg transition-colors ${
                      isDark
                        ? 'bg-gray-700 hover:bg-gray-600 text-white'
                        : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                    }`}
                  >
                    ← Назад к выбору
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

