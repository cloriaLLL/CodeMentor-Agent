export type ExerciseType = 'understanding' | 'modification' | 'creation' | 'project'
export type UnderstandingSubtype = 'choice' | 'truefalse' | 'fillblank'

export interface ExerciseData {
  exercise_id: string
  exercise_type: ExerciseType
  subtype?: string
  question: string
  options?: string[] | null
  starter_code?: string | null
  test_cases?: string | null
  reference_solution?: string | null
  correct_answer?: string | null
  explanation?: string | null
  modification_requirement?: string | null
  acceptance_criteria?: string[] | null
  evaluation_dimensions?: string[] | null
  difficulty: string
  knowledge_points: string[]
  estimated_time_min: number
  language?: string
  source?: 'chat' | 'launcher'
  conversation_id?: string
  module_key?: string
}

export interface EvaluationResult {
  passed: boolean
  score: number
  result: string
  feedback: string
  needs_reteach: boolean
  details: Record<string, unknown>
}

export interface ExerciseTypeInfo {
  type: ExerciseType
  label: string
  subtypes?: { value: string; label: string }[]
}

export interface LanguageInfo {
  language: string
  display_name: string
  file_extension: string
  installed: boolean
  supports_tests: boolean
  is_compiled: boolean
  docker_image: string | null
}

export interface LanguagesResponse {
  status: string
  languages: LanguageInfo[]
}

/**
 * 始终确保可用的语言（自研编译器 MiniLang + Bash）。
 * 即使后端 /api/languages 未返回或未安装，前端也强制显示。
 * 统一在此定义，避免多处重复。
 */
export const ENSURED_LANGUAGES: LanguageInfo[] = [
  {
    language: 'minilang',
    display_name: 'MiniLang（教学语言）',
    file_extension: '.ml',
    installed: true,
    supports_tests: true,
    is_compiled: true,
    docker_image: null,
  },
  {
    language: 'bash',
    display_name: 'Bash',
    file_extension: '.sh',
    installed: true,
    supports_tests: false,
    is_compiled: false,
    docker_image: null,
  },
]

/**
 * 理解型题目专用的扩展语言池。
 *
 * 核心思想：理解型题目（选择/判断/填空）不依赖代码沙箱运行，
 * 只需要 LLM 生成题目，因此理论上支持"无限"种编程语言。
 * 这里列出主流和常见的语言，让用户有更丰富的选择。
 *
 * 代码型题目（修改/创作/项目）仍只显示沙箱实际支持的语言。
 */
export const UNDERSTANDING_LANGUAGE_POOL: LanguageInfo[] = [
  { language: 'python', display_name: 'Python', file_extension: '.py', installed: true, supports_tests: false, is_compiled: false, docker_image: null },
  { language: 'javascript', display_name: 'JavaScript', file_extension: '.js', installed: true, supports_tests: false, is_compiled: false, docker_image: null },
  { language: 'minilang', display_name: 'MiniLang（教学语言）', file_extension: '.ml', installed: true, supports_tests: false, is_compiled: true, docker_image: null },
  { language: 'java', display_name: 'Java', file_extension: '.java', installed: false, supports_tests: false, is_compiled: true, docker_image: null },
  { language: 'csharp', display_name: 'C# (.NET)', file_extension: '.cs', installed: false, supports_tests: false, is_compiled: true, docker_image: null },
  { language: 'cpp', display_name: 'C++', file_extension: '.cpp', installed: false, supports_tests: false, is_compiled: true, docker_image: null },
  { language: 'c', display_name: 'C 语言', file_extension: '.c', installed: false, supports_tests: false, is_compiled: true, docker_image: null },
  { language: 'go', display_name: 'Go', file_extension: '.go', installed: false, supports_tests: false, is_compiled: true, docker_image: null },
  { language: 'rust', display_name: 'Rust', file_extension: '.rs', installed: false, supports_tests: false, is_compiled: true, docker_image: null },
  { language: 'typescript', display_name: 'TypeScript', file_extension: '.ts', installed: false, supports_tests: false, is_compiled: true, docker_image: null },
  { language: 'ruby', display_name: 'Ruby', file_extension: '.rb', installed: false, supports_tests: false, is_compiled: false, docker_image: null },
  { language: 'php', display_name: 'PHP', file_extension: '.php', installed: false, supports_tests: false, is_compiled: false, docker_image: null },
  { language: 'swift', display_name: 'Swift', file_extension: '.swift', installed: false, supports_tests: false, is_compiled: true, docker_image: null },
  { language: 'kotlin', display_name: 'Kotlin', file_extension: '.kt', installed: false, supports_tests: false, is_compiled: true, docker_image: null },
  { language: 'scala', display_name: 'Scala', file_extension: '.scala', installed: false, supports_tests: false, is_compiled: true, docker_image: null },
  { language: 'bash', display_name: 'Bash / Shell', file_extension: '.sh', installed: true, supports_tests: false, is_compiled: false, docker_image: null },
  { language: 'sql', display_name: 'SQL', file_extension: '.sql', installed: false, supports_tests: false, is_compiled: false, docker_image: null },
  { language: 'html', display_name: 'HTML / CSS', file_extension: '.html', installed: false, supports_tests: false, is_compiled: false, docker_image: null },
  { language: 'lua', display_name: 'Lua', file_extension: '.lua', installed: false, supports_tests: false, is_compiled: false, docker_image: null },
  { language: 'r', display_name: 'R 语言', file_extension: '.r', installed: false, supports_tests: false, is_compiled: false, docker_image: null },
]

/**
 * 代码型题目推荐排序的语言顺序（初学者友好排序）。
 * 1. Python - 最适合入门
 * 2. JavaScript - 最流行的全栈语言
 * 3. MiniLang - 我们的教学语言
 * 4. Java - 企业级主流
 * 5. C# - .NET 生态
 * 6. Bash - 脚本必备
 */
const CODE_LANGUAGE_ORDER = ['python', 'javascript', 'minilang', 'java', 'csharp', 'bash']

/**
 * 按推荐顺序对语言列表排序（初学者友好）。
 * Python 和 MiniLang 排前面，C/C++/Rust 等较难的靠后。
 */
export function sortLanguagesForBeginners(langs: LanguageInfo[]): LanguageInfo[] {
  const map = new Map(langs.map((l) => [l.language, l]))
  const result: LanguageInfo[] = []

  for (const key of CODE_LANGUAGE_ORDER) {
    const lang = map.get(key)
    if (lang) {
      result.push(lang)
      map.delete(key)
    }
  }

  for (const lang of map.values()) {
    result.push(lang)
  }

  return result
}

/**
 * 将后端返回的语言列表与 ENSURED_LANGUAGES 合并去重。
 * 统一合并逻辑，确保 MiniLang 和 Bash 始终可见。
 * 结果按初学者友好顺序排序。
 */
export function mergeLanguages(apiLanguages: LanguageInfo[]): LanguageInfo[] {
  const merged = [...apiLanguages]
  for (const ensured of ENSURED_LANGUAGES) {
    if (!merged.some((l) => l.language === ensured.language)) {
      merged.push(ensured)
    }
  }
  return sortLanguagesForBeginners(merged)
}

export interface ExerciseState {
  exercise: ExerciseData | null
  result: EvaluationResult | null
  isLoading: boolean
  isSubmitting: boolean
  isFetchingHint: boolean
  hint: string | null
  error: string | null
}

export interface ProblemSummary {
  id: number
  source: string
  source_id: string
  title: string
  difficulty: string
  tags: string
}

export interface ProblemDetail extends ProblemSummary {
  description: string
  starter_code: string | null
  test_cases: string | null
}
