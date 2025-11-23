import { Link, useNavigate } from 'react-router-dom'
import { ReactNode } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import ThemeToggle from './ThemeToggle'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const navigate = useNavigate()
  const { resolvedTheme } = useTheme()
  const token = localStorage.getItem('access_token')
  const isDark = resolvedTheme === 'dark'

  const handleLogout = async () => {
    try {
      // Пытаемся вызвать logout endpoint
      const token = localStorage.getItem('access_token')
      if (token) {
        await fetch('http://localhost:8000/api/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      navigate('/login')
    }
  }

  return (
    <div className={`min-h-screen transition-colors ${
      isDark ? 'bg-gray-900' : 'bg-gray-50'
    }`}>
      <nav className={`shadow-sm transition-colors ${
        isDark ? 'bg-gray-800 border-b border-gray-700' : 'bg-white'
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <Link to="/" className="flex items-center">
                <span className={`text-2xl font-bold ${
                  isDark ? 'text-blue-400' : 'text-blue-600'
                }`}>HAHABEST</span>
              </Link>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link
                  to="/vacancies"
                  className={`border-transparent inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors ${
                    isDark 
                      ? 'text-gray-300 hover:text-gray-100 hover:border-gray-600' 
                      : 'text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  }`}
                >
                  Вакансии
                </Link>
                {token && (
                  <>
                    <Link
                      to="/favorites"
                      className={`border-transparent inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors ${
                        isDark 
                          ? 'text-gray-300 hover:text-gray-100 hover:border-gray-600' 
                          : 'text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`}
                    >
                      Избранное
                    </Link>
                    <Link
                      to="/profile"
                      className={`border-transparent inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors ${
                        isDark 
                          ? 'text-gray-300 hover:text-gray-100 hover:border-gray-600' 
                          : 'text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`}
                    >
                      Профиль
                    </Link>
                  </>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <ThemeToggle />
              {token ? (
                <button
                  onClick={handleLogout}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isDark 
                      ? 'text-gray-300 hover:text-gray-100 hover:bg-gray-700' 
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Выйти
                </button>
              ) : (
                <>
                  <Link
                    to="/login"
                    className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isDark 
                        ? 'text-gray-300 hover:text-gray-100 hover:bg-gray-700' 
                        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    Войти
                  </Link>
                  <Link
                    to="/register"
                    className={`ml-4 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      isDark
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'bg-blue-600 text-white hover:bg-blue-700'
                    }`}
                  >
                    Регистрация
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>
      <main className={`max-w-7xl mx-auto py-6 sm:px-6 lg:px-8 transition-colors ${
        isDark ? 'text-gray-100' : 'text-gray-900'
      }`}>
        {children}
      </main>
    </div>
  )
}

