import { useState, useEffect } from 'react'
import { useNavigate, Link, useLocation } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import api from '../services/api'

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { resolvedTheme } = useTheme()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [emailError, setEmailError] = useState('')
  const [passwordError, setPasswordError] = useState('')

  useEffect(() => {
    if (location.state?.message) {
      setError('')
      // Можно показать success message
    }
  }, [location])

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!email) {
      setEmailError('Email обязателен')
      return false
    }
    if (!emailRegex.test(email)) {
      setEmailError('Некорректный формат email')
      return false
    }
    setEmailError('')
    return true
  }

  const validatePassword = (password: string) => {
    if (!password) {
      setPasswordError('Пароль обязателен')
      return false
    }
    if (password.length < 6) {
      setPasswordError('Пароль должен быть не менее 6 символов')
      return false
    }
    setPasswordError('')
    return true
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    e.stopPropagation()
    
    // Предотвращаем отправку формы, если уже загружается
    if (loading) {
      e.preventDefault()
      return false
    }
    
    setError('')
    
    const isEmailValid = validateEmail(email)
    const isPasswordValid = validatePassword(password)
    
    if (!isEmailValid || !isPasswordValid) {
      e.preventDefault()
      return false
    }

    setLoading(true)

    try {
      const formData = new URLSearchParams()
      formData.append('username', email)
      formData.append('password', password)

      const response = await api.post('/api/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        validateStatus: (status) => status < 500, // Не выбрасываем ошибку для 4xx
      })

      if (response.status === 200 || response.status === 201) {
        localStorage.setItem('access_token', response.data.access_token)
        localStorage.setItem('refresh_token', response.data.refresh_token)
        setLoading(false)
        navigate('/profile')
        return false
      } else {
        // Обработка ошибок 4xx
        const errorMessage = response.data?.detail || 'Неверный email или пароль'
        setError(errorMessage)
        setLoading(false)
        e.preventDefault()
        return false
      }
    } catch (err: any) {
      // Обработка сетевых ошибок и 5xx
      const errorMessage = err.response?.data?.detail || err.message || 'Ошибка входа. Проверьте подключение к интернету.'
      setError(errorMessage)
      setLoading(false)
      e.preventDefault()
      return false
    }
  }

  const isDark = resolvedTheme === 'dark'

  return (
    <div className={`min-h-screen flex items-center justify-center ${
      isDark 
        ? 'bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900' 
        : 'bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50'
    } py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden`}>
      {/* Декоративные элементы */}
      <div className="absolute inset-0 overflow-hidden">
        <div className={`absolute -top-40 -right-40 w-80 h-80 rounded-full ${
          isDark ? 'bg-blue-900/20' : 'bg-blue-400/20'
        } blur-3xl`}></div>
        <div className={`absolute -bottom-40 -left-40 w-80 h-80 rounded-full ${
          isDark ? 'bg-purple-900/20' : 'bg-purple-400/20'
        } blur-3xl`}></div>
      </div>

      <div className="max-w-md w-full space-y-8 relative z-10">
        <div>
          <h2 className={`mt-6 text-center text-3xl font-extrabold ${
            isDark ? 'text-white' : 'text-gray-900'
          }`}>
            Вход в HAHABEST
          </h2>
          <p className={`mt-2 text-center text-sm ${
            isDark ? 'text-gray-400' : 'text-gray-600'
          }`}>
            Или{' '}
            <Link to="/register" className="font-medium text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300">
              создайте новый аккаунт
            </Link>
          </p>
        </div>
        <div className={`rounded-xl shadow-2xl p-8 ${
          isDark ? 'bg-gray-800/90 backdrop-blur-sm' : 'bg-white/90 backdrop-blur-sm'
        } border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
          <form 
            onSubmit={(e) => {
              handleSubmit(e)
              return false
            }} 
            className="space-y-6" 
            noValidate
          >
            {error && (
              <div className={`border-l-4 p-4 rounded transition-colors ${
                error.includes('OAuth') || error.includes('Google')
                  ? isDark
                    ? 'bg-blue-900/20 border-blue-500'
                    : 'bg-blue-50 border-blue-400'
                  : isDark
                    ? 'bg-red-900/20 border-red-500'
                    : 'bg-red-50 border-red-400'
              }`}>
                <div className="flex">
                  <div className="ml-3">
                    <p className={`text-sm transition-colors ${
                      error.includes('OAuth') || error.includes('Google')
                        ? isDark
                          ? 'text-blue-300'
                          : 'text-blue-700'
                        : isDark
                          ? 'text-red-300'
                          : 'text-red-700'
                    }`}>
                      {error}
                      {error.includes('OAuth') || error.includes('Google') && (
                        <a
                          href="http://localhost:8000/api/auth/google/login"
                          className="ml-2 underline font-medium"
                        >
                          Войти через Google
                        </a>
                      )}
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div>
              <label htmlFor="email" className={`block text-sm font-medium mb-1 ${
                isDark ? 'text-gray-300' : 'text-gray-700'
              }`}>
                Email адрес
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value)
                  if (emailError) validateEmail(e.target.value)
                }}
                onBlur={() => validateEmail(email)}
                required
                className={`appearance-none relative block w-full px-3 py-2 border ${
                  emailError 
                    ? isDark
                      ? 'border-red-600 bg-gray-700/50'
                      : 'border-red-300 bg-white'
                    : isDark 
                      ? 'border-gray-600 bg-gray-700/50' 
                      : 'border-gray-300 bg-white'
                } ${
                  isDark ? 'text-white placeholder-gray-400' : 'text-gray-900 placeholder-gray-500'
                } rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-colors`}
                placeholder="your@email.com"
              />
              {emailError && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{emailError}</p>
              )}
            </div>

            <div>
              <label htmlFor="password" className={`block text-sm font-medium mb-1 ${
                isDark ? 'text-gray-300' : 'text-gray-700'
              }`}>
                Пароль
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value)
                    if (passwordError) validatePassword(e.target.value)
                  }}
                  onBlur={() => validatePassword(password)}
                  required
                  className={`appearance-none relative block w-full px-3 py-2 pr-10 border ${
                    passwordError 
                      ? isDark
                        ? 'border-red-600 bg-gray-700/50'
                        : 'border-red-300 bg-white'
                      : isDark 
                        ? 'border-gray-600 bg-gray-700/50' 
                        : 'border-gray-300 bg-white'
                  } ${
                    isDark ? 'text-white placeholder-gray-400' : 'text-gray-900 placeholder-gray-500'
                  } rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-colors`}
                  placeholder="Введите пароль"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <svg className={`h-5 w-5 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.29 3.29m0 0L12 12m-5.71-5.71L12 12" />
                    </svg>
                  ) : (
                    <svg className={`h-5 w-5 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
              {passwordError && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{passwordError}</p>
              )}
              <p className={`mt-1 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                Минимум 6 символов
              </p>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? (
                  <span className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Вход...
                  </span>
                ) : (
                  'Войти'
                )}
              </button>
            </div>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className={`absolute inset-0 flex items-center ${
                isDark ? 'border-gray-700' : 'border-gray-300'
              }`}>
                <div className={`w-full border-t ${isDark ? 'border-gray-700' : 'border-gray-300'}`}></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className={`px-2 ${isDark ? 'bg-gray-800 text-gray-400' : 'bg-white text-gray-500'}`}>или</span>
              </div>
            </div>

            <div className="mt-6">
              <a
                href="http://localhost:8000/api/auth/google/login"
                className={`w-full inline-flex justify-center items-center px-4 py-2 border rounded-lg shadow-sm text-sm font-medium transition-colors ${
                  isDark
                    ? 'border-gray-600 bg-gray-700/50 text-gray-200 hover:bg-gray-700'
                    : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                Войти через Google
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
