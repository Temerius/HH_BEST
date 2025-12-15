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
    </div>
  )
}

