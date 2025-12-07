export interface Vacancy {
  id: number
  name: string
  premium: boolean
  employer_id: number
  employer_name?: string
  area_id: string
  area_name?: string
  address_city?: string
  address_raw?: string
  address_lat?: number
  address_lng?: number
  salary_from?: number
  salary_to?: number
  salary_currency?: string
  salary_gross?: boolean
  // Полные описания для rabota.by
  description?: string
  tasks?: string
  requirements?: string
  advantages?: string
  offers?: string
  // Старые поля (для совместимости)
  snippet_requirement?: string
  snippet_responsibility?: string
  schedule_name?: string
  experience_name?: string
  employment_name?: string
  work_format_name?: string
  education_name?: string
  specialization_id?: number
  specialization_name?: string
  metro_stations?: Array<{id: number, name: string, line_name?: string}>
  skills?: string[]
  published_at: string
  alternate_url?: string
  archived: boolean
}

export interface VacancyListResponse {
  items: Vacancy[]
  total: number
  page: number
  per_page: number
}

export interface User {
  id: string
  email: string
  first_name?: string
  last_name?: string
  phone?: string
  birth_date?: string
  avatar_url?: string
  specialization?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Resume {
  id: string
  user_id: string
  title: string
  position?: string
  salary_from?: number
  salary_to?: number
  salary_currency: string
  experience_years?: number
  about?: string
  education?: string
  work_experience?: any[]
  skills_summary?: string
  languages?: any[]
  is_primary: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Skill {
  id: number
  name: string
  category?: string
  created_at: string
}

export interface UserSkill {
  skill_id: number
  skill_name: string
  skill_category?: string
  level: string
  years_of_experience?: number
}

export interface AISuggestSkillsResponse {
  recommended_skills: Array<{
    name: string
    reason: string
  }>
}

export interface AIImproveResumeResponse {
  suggestions: string[]
  improved_sections?: Record<string, string>
}

