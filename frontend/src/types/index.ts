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
  salary_from?: number
  salary_to?: number
  salary_currency?: string
  salary_gross?: boolean
  snippet_requirement?: string
  snippet_responsibility?: string
  description?: string
  schedule_name?: string
  experience_name?: string
  employment_name?: string
  work_format_name?: string
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

