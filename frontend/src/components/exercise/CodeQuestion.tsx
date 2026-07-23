import { useState, useEffect, useRef } from 'react'
import { Play, Send, RotateCcw, Terminal, Sparkles, ChevronDown, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LiquidGlassCard } from '@/components/ui/liquid-glass-card'
import { CodeEditor } from './CodeEditor'
import { useExercise } from '@/contexts/ExerciseContext'
import { exerciseApi } from '@/lib/exercise-api'
import type { ExerciseData, LanguageInfo } from '@/types/exercise'
import { mergeLanguages, ENSURED_LANGUAGES } from '@/types/exercise'

interface CodeQuestionProps {
  exercise: ExerciseData
}

/** 调用 /api/chat 对运行/评判失败做一句话纠错建议，失败静默降级。 */
async function fetchAiCorrection(
  code: string,
  errorOutput: string,
  language: string
): Promise<string | null> {
  const prompt = `你是一位编程调试助手。用户用 ${language} 写了下面的代码，运行时出现错误。请用一句话（不超过 80 字）指出最可能的错误原因与修正方向，不要给出完整代码。

代码：
\`\`\`
${code.slice(0, 1200)}
\`\`\`

错误输出：
\`\`\`
${(errorOutput || '').slice(0, 800)}
\`\`\`

请直接输出建议，不要前缀。`
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: prompt, history: [] }),
    })
    if (!res.ok) return null
    const data = await res.json()
    const reply = (data?.reply || '').trim()
    return reply ? reply.slice(0, 200) : null
  } catch {
    return null
  }
}

export function CodeQuestion({ exercise }: CodeQuestionProps) {
  const { submitAnswer, isSubmitting, updateExercise } = useExercise()
  const [code, setCode] = useState('')
  const [runOutput, setRunOutput] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [languages, setLanguages] = useState<LanguageInfo[]>([])
  const [aiHint, setAiHint] = useState<string | null>(null)
  const [isFetchingHint, setIsFetchingHint] = useState(false)
  const [langDropdownOpen, setLangDropdownOpen] = useState(false)
  const langDropdownRef = useRef<HTMLDivElement>(null)
  const isMountedRef = useRef(true)
  const language = exercise.language || 'python'

  useEffect(() => {
    isMountedRef.current = true
    return () => { isMountedRef.current = false }
  }, [])

  useEffect(() => {
    setCode(exercise.starter_code || '')
    setRunOutput(null)
    setAiHint(null)
  }, [exercise.exercise_id, exercise.starter_code])

  // 挂载时拉取支持的语言列表（供选择器渲染）
  useEffect(() => {
    let alive = true
    exerciseApi
      .getLanguages()
      .then((res) => {
        if (!alive) return
        setLanguages(mergeLanguages(res.languages || []))
      })
      .catch(() => {
        if (alive) setLanguages(ENSURED_LANGUAGES)
      })
    return () => {
      alive = false
    }
  }, [])

  // 点击外部关闭语言下拉框
  useEffect(() => {
    if (!langDropdownOpen) return
    const handleClickOutside = (e: MouseEvent) => {
      if (langDropdownRef.current && !langDropdownRef.current.contains(e.target as Node)) {
        setLangDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [langDropdownOpen])

  const handleLanguageChange = (lang: string) => {
    if (lang === language) {
      setLangDropdownOpen(false)
      return
    }
    updateExercise({ language: lang, starter_code: '' })
    setCode('')
    setRunOutput(null)
    setAiHint(null)
    setLangDropdownOpen(false)
  }

  const handleSubmit = async () => {
    if (!code.trim()) return
    setRunOutput(null)
    setAiHint(null)
    await submitAnswer(code)
  }

  const handleRun = async () => {
    if (!code.trim()) return
    setIsRunning(true)
    setRunOutput(null)
    setAiHint(null)
    try {
      const data = await exerciseApi.runCode(code, language)
      if (!isMountedRef.current) return
      const errorOutput = data.error || ''
      const output = errorOutput
        ? `错误:\n${errorOutput}`
        : data.output || '执行完成（无输出）'
      setRunOutput(`${output}${data.execution_time_sec ? `\n\n--- 耗时: ${data.execution_time_sec}s ---` : ''}`)

      // 运行失败时触发 AI 纠错辅助（静默降级）
      if (errorOutput) {
        setIsFetchingHint(true)
        const hint = await fetchAiCorrection(code, errorOutput, language)
        if (!isMountedRef.current) return
        setAiHint(hint)
        setIsFetchingHint(false)
      }
    } catch (e) {
      if (!isMountedRef.current) return
      const msg = e instanceof Error ? e.message : '未知错误'
      setRunOutput('运行失败：' + msg)
      setIsFetchingHint(true)
      const hint = await fetchAiCorrection(code, msg, language)
      if (!isMountedRef.current) return
      setAiHint(hint)
      setIsFetchingHint(false)
    } finally {
      if (isMountedRef.current) setIsRunning(false)
    }
  }

  const handleReset = () => {
    setCode(exercise.starter_code || '')
    setRunOutput(null)
    setAiHint(null)
  }

  const showStarter = exercise.exercise_type === 'modification' && exercise.starter_code
  const installedLanguages = languages.filter((l) => l.installed)

  return (
    <div className="space-y-3">
      {showStarter && exercise.modification_requirement && (
        <LiquidGlassCard className="p-3 rounded-xl" displacementScale={6}>
          <div className="text-xs font-medium text-gray-500 mb-1.5 flex items-center gap-1.5">
            <Terminal size={12} />
            修改需求
          </div>
          <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
            {exercise.modification_requirement}
          </div>
        </LiquidGlassCard>
      )}

      {exercise.acceptance_criteria && exercise.acceptance_criteria.length > 0 && (
        <div className="p-3 rounded-xl bg-blue-50/60 border border-blue-100">
          <div className="text-xs font-medium text-blue-600 mb-1.5">验收标准</div>
          <ul className="space-y-1">
            {exercise.acceptance_criteria.map((c, i) => (
              <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                <span className="text-[#3370ff] mt-0.5">•</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          {installedLanguages.length > 0 ? (
            <div ref={langDropdownRef} className="relative">
              <button
                onClick={() => setLangDropdownOpen((v) => !v)}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/60 border border-gray-200/60 text-gray-700 text-xs font-medium hover:bg-white hover:border-gray-300/80 transition-all duration-200 shadow-sm"
                title="切换编程语言"
              >
                <span className="font-mono text-[11px] tracking-wide">
                  {installedLanguages.find((l) => l.language === language)?.display_name || language}
                </span>
                <ChevronDown size={12} className={`transition-transform duration-200 text-gray-400 ${langDropdownOpen ? 'rotate-180' : ''}`} />
              </button>
              {langDropdownOpen && (
                <div
                  className="absolute top-full left-0 mt-1.5 w-44 rounded-xl overflow-hidden z-50 shadow-xl border border-gray-200/80 bg-white/95 backdrop-blur-md"
                  style={{ animation: 'fadeInDown 0.15s ease forwards' }}
                >
                  {installedLanguages.map((l) => (
                    <button
                      key={l.language}
                      onClick={() => handleLanguageChange(l.language)}
                      className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between transition-colors ${
                        language === l.language
                          ? 'bg-blue-50 text-[#3370ff] font-medium'
                          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-800'
                      }`}
                    >
                      <span className="font-mono text-[11px] tracking-wide">
                        {l.display_name}
                      </span>
                      {language === l.language && <Check size={12} className="text-[#3370ff]" />}
                    </button>
                  ))}
                  {!installedLanguages.some((l) => l.language === language) && (
                    <button
                      onClick={() => setLangDropdownOpen(false)}
                      className="w-full text-left px-3 py-2 text-xs text-gray-400 flex items-center justify-between"
                    >
                      <span className="font-mono text-[11px]">{language}（未安装）</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          ) : (
            <span className="px-2.5 py-1 rounded-lg bg-white/60 border border-gray-200/60 text-gray-600 font-mono text-[11px] tracking-wide">
              {language}
            </span>
          )}
          <span className="text-gray-300">·</span>
          <span>{exercise.estimated_time_min}分钟</span>
        </div>
        <button
          onClick={handleReset}
          className="text-xs text-gray-400 hover:text-[#3370ff] flex items-center gap-1 transition-colors"
        >
          <RotateCcw size={11} />
          重置
        </button>
      </div>

      <CodeEditor
        value={code}
        onChange={setCode}
        language={language}
        minHeight={280}
        placeholder={exercise.exercise_type === 'creation' ? '从零开始编写你的代码...' : '在此修改代码...'}
      />

      <div className="flex gap-2">
        <Button
          variant="outline"
          className="flex-1 h-10"
          onClick={handleRun}
          disabled={!code.trim() || isRunning}
        >
          <Play size={14} />
          {isRunning ? '运行中...' : '运行测试'}
        </Button>
        <Button
          variant="primary"
          className="flex-1 h-10"
          onClick={handleSubmit}
          disabled={!code.trim() || isSubmitting}
        >
          <Send size={14} />
          {isSubmitting ? '评判中...' : '提交评判'}
        </Button>
      </div>

      {runOutput !== null && (
        <LiquidGlassCard className="rounded-xl overflow-hidden" displacementScale={4}>
          <div className="px-3 py-2 border-b border-black/5 flex items-center gap-1.5 text-xs text-gray-500">
            <Terminal size={12} />
            运行输出
          </div>
          <pre className="p-3 text-xs font-mono text-gray-700 whitespace-pre-wrap max-h-48 overflow-y-auto bg-black/2">
            {runOutput}
          </pre>
        </LiquidGlassCard>
      )}

      {isFetchingHint && (
        <div className="px-3 py-2 rounded-xl bg-purple-50/60 border border-purple-100 text-xs text-purple-600 flex items-center gap-1.5">
          <Sparkles size={12} className="animate-pulse" />
          AI 正在分析错误...
        </div>
      )}

      {aiHint && (
        <LiquidGlassCard className="p-3 rounded-xl" displacementScale={4}>
          <div className="text-xs font-medium text-purple-600 mb-1.5 flex items-center gap-1.5">
            <Sparkles size={12} />
            AI 纠错建议
          </div>
          <div className="text-sm text-gray-700 leading-relaxed">{aiHint}</div>
        </LiquidGlassCard>
      )}

      <style>{`
        @keyframes fadeInDown {
          from { opacity: 0; transform: translateY(-6px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
