import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import api from '../services/api'
import { User, UserSkill, Skill, AISuggestSkillsResponse } from '../types'

export default function EditProfilePage() {
  const navigate = useNavigate()
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const [user, setUser] = useState<User | null>(null)
  const [userSkills, setUserSkills] = useState<UserSkill[]>([])
  const [availableSkills, setAvailableSkills] = useState<any[]>([])
  const [skillCategories, setSkillCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [aiSuggestions, setAiSuggestions] = useState<AISuggestSkillsResponse | null>(null)
  const [loadingAI, setLoadingAI] = useState(false)
  const [searchSkill, setSearchSkill] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [specializations, setSpecializations] = useState<string[]>([])
  
  // Локальное состояние для изменений (не применяется до сохранения)
  const [localUser, setLocalUser] = useState<User | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      navigate('/login')
      return
    }
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [userResponse, skillsResponse, mySkillsResponse, specializationsResponse, categoriesResponse] = await Promise.all([
        api.get('/api/users/me'),
        api.get('/api/metadata/skills'),
        api.get('/api/skills/my'),
        api.get('/api/metadata/specializations'),
        api.get('/api/metadata/skill-categories')
      ])
      setUser(userResponse.data)
      setLocalUser({ ...userResponse.data }) // Копируем для локального редактирования
      
      // Фильтруем навыки по поиску и категории
      let filteredSkills = skillsResponse.data
      if (searchSkill) {
        filteredSkills = filteredSkills.filter((skill: any) => 
          skill.name.toLowerCase().includes(searchSkill.toLowerCase())
        )
      }
      if (selectedCategory) {
        filteredSkills = filteredSkills.filter((skill: any) => 
          skill.category === selectedCategory
        )
      }
      setAvailableSkills(filteredSkills)
      setUserSkills(mySkillsResponse.data)
      setSpecializations(specializationsResponse.data)
      setSkillCategories(categoriesResponse.data)
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!loading) {
      loadData()
    }
  }, [searchSkill, selectedCategory])

  const handleUpdateUser = (field: string, value: any) => {
    // Обновляем только локальное состояние
    if (localUser) {
      setLocalUser({ ...localUser, [field]: value })
    }
  }

  const handleSaveUser = async () => {
    if (!localUser) return
    
    try {
      setSaving(true)
      const response = await api.put('/api/users/me', {
        specialization: localUser.specialization
      })
      setUser(response.data)
      setLocalUser({ ...response.data })
      alert('Профиль успешно сохранен')
    } catch (error) {
      console.error('Error updating user:', error)
      alert('Ошибка при обновлении профиля')
    } finally {
      setSaving(false)
    }
  }

  const handleAddSkill = async (skillName: string, skillCategory?: string) => {
    try {
      await api.post('/api/skills/my', {
        skill_name: skillName,
        skill_category: skillCategory,
        level: 'intermediate',
        years_of_experience: null
      })
      loadData()
    } catch (error: any) {
      if (error.response?.status === 400) {
        alert('Этот навык уже добавлен')
      } else {
        console.error('Error adding skill:', error)
        alert('Ошибка при добавлении навыка')
      }
    }
  }

  const handleRemoveSkill = async (skillId: number) => {
    try {
      await api.delete(`/api/skills/my/${skillId}`)
      loadData()
    } catch (error) {
      console.error('Error removing skill:', error)
      alert('Ошибка при удалении навыка')
    }
  }

  const handleUpdateSkill = async (skillId: number, level: string, years?: number) => {
    try {
      await api.put(`/api/skills/my/${skillId}`, {
        level,
        years_of_experience: years
      })
      loadData()
    } catch (error) {
      console.error('Error updating skill:', error)
      alert('Ошибка при обновлении навыка')
    }
  }

  const handleGetAISuggestions = async () => {
    if (!localUser?.specialization) {
      alert('Сначала выберите направление разработки')
      return
    }
    
    setLoadingAI(true)
    try {
      const response = await api.post<AISuggestSkillsResponse>('/api/ai/suggest-skills', {
        specialization: localUser.specialization
      })
      setAiSuggestions(response.data)
    } catch (error) {
      console.error('Error getting AI suggestions:', error)
      alert('Ошибка при получении рекомендаций')
    } finally {
      setLoadingAI(false)
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
    <div className="px-4 py-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className={`text-3xl font-bold transition-colors ${
          isDark ? 'text-white' : 'text-gray-900'
        }`}>Редактирование профиля</h1>
        <Link
          to="/profile"
          className={`px-4 py-2 rounded-lg transition-colors ${
            isDark
              ? 'bg-gray-700 text-gray-200 hover:bg-gray-600'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Назад к профилю
        </Link>
      </div>

      {localUser && (
        <>
          {/* Основная информация */}
          <div className={`rounded-lg shadow-sm p-6 mb-6 transition-colors ${
            isDark 
              ? 'bg-gray-800/50 border border-gray-700' 
              : 'bg-white'
          }`}>
            <div className="flex justify-between items-center mb-4">
              <h2 className={`text-xl font-semibold transition-colors ${
                isDark ? 'text-white' : 'text-gray-900'
              }`}>Основная информация</h2>
              <button
                onClick={handleSaveUser}
                disabled={saving}
                className={`px-6 py-2 rounded-lg transition-colors ${
                  isDark
                    ? 'bg-green-600 hover:bg-green-700 text-white'
                    : 'bg-green-500 hover:bg-green-600 text-white'
                } disabled:opacity-50`}
              >
                {saving ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className={`block text-sm font-medium mb-1 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  Направление разработки
                </label>
                <select
                  value={localUser?.specialization || ''}
                  onChange={(e) => handleUpdateUser('specialization', e.target.value || null)}
                  className={`w-full px-3 py-2 border rounded-lg transition-colors ${
                    isDark
                      ? 'border-gray-600 bg-gray-700/50 text-white'
                      : 'border-gray-300 bg-white text-gray-900'
                  }`}
                >
                  <option value="">Не выбрано</option>
                  {specializations.map(spec => (
                    <option key={spec} value={spec}>{spec}</option>
                  ))}
                </select>
                {localUser?.specialization && (
                  <button
                    onClick={handleGetAISuggestions}
                    disabled={loadingAI}
                    className={`mt-2 px-4 py-2 rounded-lg text-sm transition-colors ${
                      isDark
                        ? 'bg-blue-600 hover:bg-blue-700 text-white'
                        : 'bg-blue-500 hover:bg-blue-600 text-white'
                    } disabled:opacity-50`}
                  >
                    {loadingAI ? 'Загрузка...' : 'Получить рекомендации по навыкам'}
                  </button>
                )}
              </div>

              {aiSuggestions && (
                <div className={`mt-4 p-4 rounded-lg border transition-colors ${
                  isDark
                    ? 'bg-blue-900/20 border-blue-700'
                    : 'bg-blue-50 border-blue-200'
                }`}>
                  <h3 className={`font-semibold mb-2 ${
                    isDark ? 'text-blue-300' : 'text-blue-900'
                  }`}>Рекомендации ИИ:</h3>
                  <ul className="space-y-2">
                    {aiSuggestions.recommended_skills.map((skill, idx) => (
                      <li key={idx} className={`text-sm ${
                        isDark ? 'text-blue-200' : 'text-blue-800'
                      }`}>
                        <strong>{skill.name}:</strong> {skill.reason}
                        {!userSkills.find(us => us.skill_name === skill.name) && (
                          <button
                            onClick={() => handleAddSkill(skill.name)}
                            className={`ml-2 px-2 py-1 text-xs rounded transition-colors ${
                              isDark
                                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                                : 'bg-blue-500 hover:bg-blue-600 text-white'
                            }`}
                          >
                            Добавить
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Навыки */}
          <div className={`rounded-lg shadow-sm p-6 mb-6 transition-colors ${
            isDark 
              ? 'bg-gray-800/50 border border-gray-700' 
              : 'bg-white'
          }`}>
            <h2 className={`text-xl font-semibold mb-4 transition-colors ${
              isDark ? 'text-white' : 'text-gray-900'
            }`}>Мои навыки</h2>

            {/* Поиск навыков */}
            <div className="mb-4 space-y-2">
              <input
                type="text"
                placeholder="Поиск навыков..."
                value={searchSkill}
                onChange={(e) => setSearchSkill(e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg transition-colors ${
                  isDark
                    ? 'border-gray-600 bg-gray-700/50 text-white placeholder-gray-400'
                    : 'border-gray-300 bg-white text-gray-900 placeholder-gray-500'
                }`}
              />
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg transition-colors ${
                  isDark
                    ? 'border-gray-600 bg-gray-700/50 text-white'
                    : 'border-gray-300 bg-white text-gray-900'
                }`}
              >
                <option value="">Все категории</option>
                <option value="programming">Programming</option>
                <option value="devops">DevOps</option>
                <option value="tools">Tools</option>
                <option value="methodology">Methodology</option>
              </select>
            </div>

            {/* Мои навыки */}
            {userSkills.length > 0 && (
              <div className="mb-6">
                <h3 className={`text-lg font-medium mb-3 ${
                  isDark ? 'text-gray-300' : 'text-gray-700'
                }`}>Добавленные навыки:</h3>
                <div className="flex flex-wrap gap-2">
                  {userSkills.map((userSkill) => (
                    <div
                      key={userSkill.skill_id}
                      className={`px-3 py-2 rounded-lg border transition-colors ${
                        isDark
                          ? 'bg-gray-700/50 border-gray-600'
                          : 'bg-gray-100 border-gray-300'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className={`font-medium ${
                          isDark ? 'text-white' : 'text-gray-900'
                        }`}>{userSkill.skill_name}</span>
                        <select
                          value={userSkill.level}
                          onChange={(e) => handleUpdateSkill(userSkill.skill_id, e.target.value, userSkill.years_of_experience)}
                          className={`text-xs px-2 py-1 rounded border transition-colors ${
                            isDark
                              ? 'border-gray-600 bg-gray-800 text-white'
                              : 'border-gray-300 bg-white text-gray-900'
                          }`}
                        >
                          <option value="beginner">Начальный</option>
                          <option value="intermediate">Средний</option>
                          <option value="advanced">Продвинутый</option>
                          <option value="expert">Эксперт</option>
                        </select>
                        <button
                          onClick={() => handleRemoveSkill(userSkill.skill_id)}
                          className={`text-red-500 hover:text-red-700 transition-colors ${
                            isDark ? 'hover:text-red-400' : ''
                          }`}
                        >
                          ×
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Доступные навыки */}
            <div>
              <h3 className={`text-lg font-medium mb-3 ${
                isDark ? 'text-gray-300' : 'text-gray-700'
              }`}>Доступные навыки:</h3>
              <div className="flex flex-wrap gap-2 max-h-64 overflow-y-auto">
                {availableSkills
                  .filter(skill => !userSkills.find(us => us.skill_name === skill.name))
                  .map((skill) => (
                    <button
                      key={skill.name}
                      onClick={() => handleAddSkill(skill.name, skill.category)}
                      className={`px-3 py-2 rounded-lg border transition-colors ${
                        isDark
                          ? 'bg-gray-700/30 border-gray-600 text-gray-300 hover:bg-gray-700/50'
                          : 'bg-gray-50 border-gray-300 text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      {skill.name}
                    </button>
                  ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

