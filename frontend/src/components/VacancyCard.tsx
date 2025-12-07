import { Link } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import { Vacancy } from '../types'

interface VacancyCardProps {
  vacancy: Vacancy
}

export default function VacancyCard({ vacancy }: VacancyCardProps) {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'

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
            {vacancy.work_format_name && (
              <span className={`px-2 py-1 rounded text-sm transition-colors ${
                isDark 
                  ? 'bg-gray-700 text-gray-300' 
                  : 'bg-gray-100 text-gray-700'
              }`}>
                {vacancy.work_format_name}
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
        </div>
      </div>
    </Link>
  )
}

