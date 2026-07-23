import { useState, useEffect, useRef } from 'react'
import { Dumbbell, ChevronDown, Loader2, Code2 } from 'lucide-react'
import { LiquidGlassCard } from '@/components/ui/liquid-glass-card'
import { useExercise } from '@/contexts/ExerciseContext'
import { useChat } from '@/contexts/ChatContext'
import { cn } from '@/lib/utils'
import { exerciseApi } from '@/lib/exercise-api'
import type { ExerciseType, UnderstandingSubtype, LanguageInfo } from '@/types/exercise'
import { mergeLanguages, ENSURED_LANGUAGES, UNDERSTANDING_LANGUAGE_POOL, sortLanguagesForBeginners } from '@/types/exercise'

interface QuickOption {
  label: string
  exercise_type: ExerciseType
  subtype?: UnderstandingSubtype
  knowledge_point: string
  difficulty?: string
  emoji: string
}

const LANG_KNOWLEDGE_BASE: Record<string, string> = {
  python: 'Python基础',
  javascript: 'JavaScript基础',
  java: 'Java基础',
  'csharp': 'C#基础',
  bash: 'Bash脚本',
  minilang: 'MiniLang基础',
  ml: 'MiniLang基础',
  cpp: 'C++基础',
  c: 'C语言基础',
  go: 'Go语言基础',
  rust: 'Rust基础',
  typescript: 'TypeScript基础',
  ruby: 'Ruby基础',
  php: 'PHP基础',
  swift: 'Swift基础',
  kotlin: 'Kotlin基础',
  scala: 'Scala基础',
  sql: 'SQL基础',
  html: 'HTML/CSS基础',
  lua: 'Lua基础',
  r: 'R语言基础',
}

export function ExerciseLauncher() {
  const { generateExercise, panelOpen, isLoading } = useExercise()
  const { getCurrentMessages, isGenerating } = useChat()
  const [expanded, setExpanded] = useState(false)
  const [lastMessageId, setLastMessageId] = useState<string | null>(null)
  const [languages, setLanguages] = useState<LanguageInfo[]>([])
  const [codeLanguages, setCodeLanguages] = useState<LanguageInfo[]>([])
  const [selectedLang, setSelectedLang] = useState('python')
  const [selectedCodeLang, setSelectedCodeLang] = useState('python')
  const [selectedUnderstandLang, setSelectedUnderstandLang] = useState('python')
  const [langDropdownOpen, setLangDropdownOpen] = useState(false)
  const [activeSection, setActiveSection] = useState<'understanding' | 'code'>('understanding')
  const containerRef = useRef<HTMLDivElement>(null)
  const langDropdownRef = useRef<HTMLDivElement>(null)

  const messages = getCurrentMessages()
  const lastMessage = messages[messages.length - 1]

  const isMountedRef = useRef(true)

  useEffect(() => {
    isMountedRef.current = true
    exerciseApi
      .getLanguages()
      .then((res) => {
        if (!isMountedRef.current) return
        const installed = (res.languages || []).filter((l) => l.installed)
        const mergedCodeLangs = mergeLanguages(installed)
        setCodeLanguages(mergedCodeLangs)
        if (mergedCodeLangs.length > 0 && !mergedCodeLangs.some((l) => l.language === selectedCodeLang)) {
          setSelectedCodeLang(mergedCodeLangs[0].language)
        }
        // 理解型语言池按初学者友好顺序排序
        setLanguages(sortLanguagesForBeginners(UNDERSTANDING_LANGUAGE_POOL))
      })
      .catch(() => {
        if (!isMountedRef.current) return
        setCodeLanguages(ENSURED_LANGUAGES)
        setLanguages(sortLanguagesForBeginners(UNDERSTANDING_LANGUAGE_POOL))
      })
    return () => { isMountedRef.current = false }
  }, [])

  useEffect(() => {
    if (!lastMessage || lastMessage.id === lastMessageId) return
    setLastMessageId(lastMessage.id)

    if (lastMessage.role === 'assistant' && !isGenerating) {
      const content = lastMessage.content.toLowerCase()
      if (content.includes('练习巩固') || content.includes('开始练习') || content.includes('做个练习')) {
        setExpanded(true)
      }
    }
  }, [lastMessage, lastMessageId, isGenerating])

  useEffect(() => {
    if (!expanded) return
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node) &&
        langDropdownRef.current &&
        !langDropdownRef.current.contains(e.target as Node)
      ) {
        setExpanded(false)
        setLangDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [expanded])

  const understandingOptions: QuickOption[] = [
    { label: '选择题', exercise_type: 'understanding', subtype: 'choice', knowledge_point: '基础语法', emoji: '📝' },
    { label: '判断题', exercise_type: 'understanding', subtype: 'truefalse', knowledge_point: '基础概念', emoji: '✓' },
    { label: '填空题', exercise_type: 'understanding', subtype: 'fillblank', knowledge_point: '核心知识', emoji: '✏️' },
  ]

  const codeOptions: QuickOption[] = [
    { label: '代码修改', exercise_type: 'modification', knowledge_point: '代码调试', emoji: '🔧' },
    { label: '代码创作', exercise_type: 'creation', knowledge_point: '算法实现', emoji: '💻' },
    { label: '综合项目', exercise_type: 'project', knowledge_point: '项目实战', emoji: '🎯' },
  ]

  const allOptions = [...understandingOptions, ...codeOptions]

  const handleLaunch = (opt: QuickOption) => {
    const lastUserMsg = [...messages].reverse().find(m => m.role === 'user')
    const isUnderstandingType = opt.exercise_type === 'understanding'
    const langToUse = isUnderstandingType ? selectedUnderstandLang : selectedCodeLang
    const baseKp = LANG_KNOWLEDGE_BASE[langToUse] || opt.knowledge_point
    const kp = lastUserMsg
      ? lastUserMsg.content.replace(/帮我|请|生成|来一道|做一道|练习|题目|关于|的|选择题|判断题|填空题|修改|编写|项目|简单|中等|困难/g, '').trim().slice(0, 40)
      : baseKp

    generateExercise({
      exercise_type: opt.exercise_type,
      knowledge_point: kp || baseKp,
      difficulty: 'Medium',
      subtype: opt.subtype,
      language: langToUse,
    })
    setExpanded(false)
    setLangDropdownOpen(false)
  }

  const currentDisplayLang = activeSection === 'understanding'
    ? languages.find((l) => l.language === selectedUnderstandLang)?.display_name || selectedUnderstandLang
    : codeLanguages.find((l) => l.language === selectedCodeLang)?.display_name || selectedCodeLang

  const displayLanguages = activeSection === 'understanding' ? languages : codeLanguages

  const handleLangSelect = (lang: string) => {
    if (activeSection === 'understanding') {
      setSelectedUnderstandLang(lang)
    } else {
      setSelectedCodeLang(lang)
    }
    setLangDropdownOpen(false)
  }

  return (
    <div ref={containerRef} className="flex flex-col items-end gap-2">
      {expanded && (
        <div
          style={{ animation: 'fadeInDown 0.2s ease forwards' }}
        >
          <LiquidGlassCard
            displacementScale={8}
            blur={16}
            className="rounded-2xl p-2 w-[200px]"
          >
            <div className="text-[10px] text-gray-400 px-2 py-1 font-medium uppercase tracking-wider flex items-center justify-between">
              <span>快速生成题目</span>
            </div>

            {languages.length > 0 && (
              <div ref={langDropdownRef} className="relative px-2 pb-2 mb-1 border-b border-black/5">
                <button
                  onClick={() => setLangDropdownOpen((v) => !v)}
                  className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg bg-blue-50/50 text-[11px] text-[#3370ff] font-medium hover:bg-blue-50/80 transition-colors"
                >
                  <span className="flex items-center gap-1.5">
                    <Code2 size={11} />
                    {currentDisplayLang}
                  </span>
                  <ChevronDown size={10} className={cn('transition-transform', langDropdownOpen && 'rotate-180')} />
                </button>
                {langDropdownOpen && (
                  <div className="absolute top-full left-2 right-2 mt-1 rounded-lg bg-white/95 backdrop-blur-md shadow-lg border border-gray-100 overflow-hidden z-50 max-h-[280px] overflow-y-auto">
                    {displayLanguages.map((l) => (
                      <button
                        key={l.language}
                        onClick={() => handleLangSelect(l.language)}
                        className={cn(
                          'w-full text-left px-2.5 py-1.5 text-[11px] transition-colors flex items-center justify-between',
                          (activeSection === 'understanding' ? selectedUnderstandLang : selectedCodeLang) === l.language
                            ? 'bg-blue-50 text-[#3370ff] font-medium'
                            : 'text-gray-600 hover:bg-gray-50'
                        )}
                      >
                        <span>{l.display_name}</span>
                        {!l.installed && activeSection === 'code' && (
                          <span className="text-[9px] text-gray-400">仅理论题</span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="px-2 pt-1 pb-1">
              <div className="text-[9px] text-gray-400 font-medium uppercase tracking-wider mb-1">理解型题目</div>
            </div>
            {understandingOptions.map(opt => (
              <button
                key={opt.label}
                onClick={() => { setActiveSection('understanding'); handleLaunch(opt) }}
                onMouseEnter={() => setActiveSection('understanding')}
                disabled={isLoading}
                className="w-full text-left px-2 py-2 rounded-lg text-xs flex items-center gap-2 transition-colors hover:bg-blue-50/80 text-gray-600 hover:text-[#3370ff] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span className="text-sm">{opt.emoji}</span>
                <span className="flex-1">{opt.label}</span>
                {isLoading && (
                  <Loader2 size={11} className="animate-spin text-[#3370ff]" />
                )}
              </button>
            ))}

            <div className="px-2 pt-2 pb-1 border-t border-black/5 mt-1">
              <div className="text-[9px] text-gray-400 font-medium uppercase tracking-wider mb-1">代码练习</div>
            </div>
            {codeOptions.map(opt => (
              <button
                key={opt.label}
                onClick={() => { setActiveSection('code'); handleLaunch(opt) }}
                onMouseEnter={() => setActiveSection('code')}
                disabled={isLoading}
                className="w-full text-left px-2 py-2 rounded-lg text-xs flex items-center gap-2 transition-colors hover:bg-blue-50/80 text-gray-600 hover:text-[#3370ff] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span className="text-sm">{opt.emoji}</span>
                <span className="flex-1">{opt.label}</span>
                {isLoading && (
                  <Loader2 size={11} className="animate-spin text-[#3370ff]" />
                )}
              </button>
            ))}
          </LiquidGlassCard>
        </div>
      )}

      <button
        onClick={() => setExpanded(e => !e)}
        disabled={isGenerating || isLoading}
        className={cn(
          'flex items-center gap-1.5 px-3 h-9 rounded-full liquid-glass-base',
          'text-xs font-medium text-gray-600 hover:text-[#3370ff]',
          'transition-all duration-200 hover:shadow-[0_8px_24px_rgba(0,0,0,0.08)]',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          panelOpen && 'bg-blue-50/70 text-[#3370ff]'
        )}
        title="练习题目"
      >
        {isLoading ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Dumbbell size={14} />
        )}
        <span>练习</span>
        <ChevronDown
          size={12}
          className={cn('transition-transform', expanded && 'rotate-180')}
        />
      </button>

      <style>{`
        @keyframes fadeInDown {
          from { opacity: 0; transform: translateY(-8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
