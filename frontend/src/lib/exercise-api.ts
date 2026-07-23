import type {
  ExerciseData,
  EvaluationResult,
  ExerciseType,
  ExerciseTypeInfo,
  LanguagesResponse,
  ProblemSummary,
  ProblemDetail,
} from '@/types/exercise'

const API_BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`请求失败 (${res.status}): ${text.slice(0, 200)}`)
  }
  return res.json() as Promise<T>
}

export const exerciseApi = {
  getTypes(): Promise<{ status: string; types: ExerciseTypeInfo[] }> {
    return request(`${API_BASE}/exercise/types`)
  },

  generate(params: {
    exercise_type: ExerciseType
    knowledge_point: string
    difficulty?: string
    subtype?: string
    session_id?: string
    language?: string
  }): Promise<{ status: string } & ExerciseData> {
    return request(`${API_BASE}/exercise/generate`, {
      method: 'POST',
      body: JSON.stringify(params),
    })
  },

  submit(payload: {
    exercise_type: ExerciseType
    question: string
    options?: string[] | null
    correct_answer?: string | null
    explanation?: string | null
    starter_code?: string | null
    reference_solution?: string | null
    test_cases?: string | null
    modification_requirement?: string | null
    acceptance_criteria?: string[] | null
    evaluation_dimensions?: string[] | null
    difficulty?: string
    knowledge_points?: string[]
    subtype?: string | null
    user_answer: string
    session_id?: string
    language?: string
  }): Promise<{ status: string } & EvaluationResult> {
    return request(`${API_BASE}/exercise/submit`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  runCode(code: string, language: string): Promise<{
    status: string
    output: string
    error: string
    execution_time_sec: number
  }> {
    return request(`${API_BASE}/exercise/run`, {
      method: 'POST',
      body: JSON.stringify({ code, language }),
    })
  },

  getLanguages(): Promise<LanguagesResponse> {
    return request(`${API_BASE}/languages`)
  },

  listProblems(params?: {
    source?: string
    tag?: string
    difficulty?: string
    limit?: number
    offset?: number
  }): Promise<{ status: string; problems: ProblemSummary[]; total: number }> {
    const qs = new URLSearchParams()
    if (params?.source) qs.set('source', params.source)
    if (params?.tag) qs.set('tag', params.tag)
    if (params?.difficulty) qs.set('difficulty', params.difficulty)
    if (params?.limit) qs.set('limit', String(params.limit))
    if (params?.offset) qs.set('offset', String(params.offset))
    const query = qs.toString()
    return request(`${API_BASE}/problems${query ? '?' + query : ''}`)
  },

  getProblem(id: number): Promise<{ status: string; problem: ProblemDetail }> {
    return request(`${API_BASE}/problems/${id}`)
  },

  getProblemMeta(): Promise<{ status: string; tags: string[]; sources: { id: string; name: string }[] }> {
    return request(`${API_BASE}/problems/meta/tags`)
  },

  clearModule(params: {
    language: string
    exercise_type: string
    subtype?: string | null
  }): Promise<{ status: string; module_key: string; cleared: boolean }> {
    return request(`${API_BASE}/exercise/clear-module`, {
      method: 'POST',
      body: JSON.stringify(params),
    })
  },
}
