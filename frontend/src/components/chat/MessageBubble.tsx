import { useState, useMemo, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Copy, Check, RotateCcw, Play, Code2, PencilLine, ExternalLink } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { LiquidGlassCard } from '@/components/ui/liquid-glass-card'
import { useExercise } from '@/contexts/ExerciseContext'
import type { Message } from '@/types'

interface MessageBubbleProps {
  message: Message
  isLast?: boolean
  onRegenerate?: () => void
}

const sectionEmojiMap: Record<string, string> = {
  '代码示例': '💻',
  '代码示范': '💻',
  '示例代码': '💻',
  '概念定义': '📌',
  '定义': '📌',
  '原理剖析': '🔬',
  '原理': '🔬',
  '工作原理': '🔬',
  '最佳实践': '✨',
  '实践建议': '✨',
  '建议': '✨',
  '常见误区': '⚠️',
  '注意事项': '⚠️',
  '警告': '⚠️',
  '延伸思考': '💡',
  '思考题': '💡',
  '思考': '💡',
  '语法/API详解': '📖',
  '语法': '📖',
  'API': '📖',
  '用法': '📖',
}

function processContent(content: string): string {
  if (!content) return content
  return content.replace(
    /(^|\n)(概念定义|定义|原理剖析|原理|工作原理|最佳实践|实践建议|建议|常见误区|注意事项|警告|延伸思考|思考题|思考|语法\/API详解|语法|API|用法|代码示例|代码示范|示例代码)[：:]\s*/g,
    (match, prefix, label) => {
      const emoji = sectionEmojiMap[label]
      if (emoji) return `${prefix}**${emoji} ${label}**：`
      return match
    }
  )
}

function extractCodeBlocks(content: string): { code: string; language: string }[] {
  const blocks: { code: string; language: string }[] = []
  const regex = /```(\w*)\n([\s\S]*?)```/g
  let m
  while ((m = regex.exec(content)) !== null) {
    blocks.push({ language: m[1] || 'python', code: m[2] })
  }
  return blocks
}

function detectExerciseInContent(content: string): { isExercise: boolean; question: string; starterCode?: string; testCases?: string; language?: string } {
  const codeBlocks = extractCodeBlocks(content)
  const hasCode = codeBlocks.length > 0

  const hasProgrammingContext =
    content.includes('变量') || content.includes('函数') ||
    content.includes('循环') || content.includes('输出') ||
    content.includes('返回') || content.includes('参数') ||
    content.includes('方法') || content.includes('类') ||
    content.includes('数组') || content.includes('字符串') ||
    content.includes('列表') || content.includes('字典') ||
    content.includes('算法') || content.includes('排序')

  const exerciseKeywords = [
    '题目', '练习', '习题', '编程题', '选择题', '判断题',
    '填空题', '练一练', '动手', '尝试', '挑战', '作业',
    '测验', '考核', '测试一下', '实现一下', '编写一个'
  ]

  const hasExerciseKeyword = exerciseKeywords.some(kw => content.includes(kw))

  const codeTaskKeywords = ['编写', '实现', '完成', '修改', '补全', '写一个', '写个']
  const hasCodeTaskKeyword = codeTaskKeywords.some(kw => content.includes(kw))

  const isStrongExercise = hasExerciseKeyword && (hasCode || hasProgrammingContext)
  const isCodeTask = hasCode && hasCodeTaskKeyword
  const hasTestPrompt = content.includes('测试') || content.includes('样例') || content.includes('输入输出')

  if (isStrongExercise || isCodeTask || (hasCode && hasTestPrompt)) {
    const cleanedQuestion = content
      .replace(/\n{3,}/g, '\n\n')
      .slice(0, 1500)
      .trim()

    let testCases: string | undefined
    if (codeBlocks.length > 1) {
      testCases = codeBlocks[1].code
    }

    return {
      isExercise: true,
      question: cleanedQuestion,
      starterCode: codeBlocks.length > 0 ? codeBlocks[0].code : undefined,
      testCases,
      language: codeBlocks.length > 0 ? codeBlocks[0].language : undefined,
    }
  }

  return { isExercise: false, question: '' }
}

function CodeBlockActions({ language, getCode }: { language: string; getCode: () => string }) {
  const [copied, setCopied] = useState(false)
  const [runOutput, setRunOutput] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [popupStyle, setPopupStyle] = useState<React.CSSProperties>({})
  const containerRef = useRef<HTMLDivElement>(null)
  const popupRef = useRef<HTMLDivElement>(null)
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const closePopupTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { openCodeEditor } = useExercise()

  useEffect(() => {
    return () => {
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current)
      if (closePopupTimerRef.current) clearTimeout(closePopupTimerRef.current)
    }
  }, [])

  useEffect(() => {
    if (runOutput === null) return
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node) &&
        popupRef.current &&
        !popupRef.current.contains(e.target as Node)
      ) {
        setRunOutput(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [runOutput])

  const startCloseTimer = () => {
    if (closePopupTimerRef.current) clearTimeout(closePopupTimerRef.current)
    closePopupTimerRef.current = setTimeout(() => setRunOutput(null), 300)
  }

  const cancelCloseTimer = () => {
    if (closePopupTimerRef.current) {
      clearTimeout(closePopupTimerRef.current)
      closePopupTimerRef.current = null
    }
  }

  const handleCopy = async () => {
    const code = getCode()
    await navigator.clipboard.writeText(code)
    setCopied(true)
    if (copyTimerRef.current) clearTimeout(copyTimerRef.current)
    copyTimerRef.current = setTimeout(() => setCopied(false), 1600)
  }

  const calculatePopupPosition = () => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const viewportHeight = window.innerHeight
    const popupMaxHeight = 224
    const spaceBelow = viewportHeight - rect.bottom
    const spaceAbove = rect.top

    if (spaceBelow < popupMaxHeight && spaceAbove > spaceBelow) {
      setPopupStyle({
        bottom: `${viewportHeight - rect.top + 8}px`,
        top: 'auto',
        right: `${window.innerWidth - rect.right}px`,
      })
    } else {
      setPopupStyle({
        top: `${rect.bottom + 8}px`,
        bottom: 'auto',
        right: `${window.innerWidth - rect.right}px`,
      })
    }
  }

  const handleRun = async () => {
    if (isRunning) return
    const supportedLangs = ['python', 'javascript', 'js', 'minilang', 'ml', 'mini']
    if (!supportedLangs.includes(language.toLowerCase())) {
      setRunOutput('该语言暂不支持在线运行')
      setTimeout(calculatePopupPosition, 0)
      return
    }
    setIsRunning(true)
    setRunOutput(null)
    try {
      const code = getCode()
      const runLang = language.toLowerCase() === 'js' ? 'javascript'
        : language.toLowerCase() === 'ml' || language.toLowerCase() === 'mini' ? 'minilang'
        : language
      const res = await fetch('/api/exercise/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, language: runLang }),
      })
      const data = await res.json()
      if (data.error) {
        setRunOutput(`错误:\n${data.error}`)
      } else {
        setRunOutput((data.output || '(无输出)') + (data.execution_time_sec ? `\n--- 耗时: ${data.execution_time_sec}s ---` : ''))
      }
      setTimeout(calculatePopupPosition, 0)
    } catch {
      setRunOutput('运行失败')
      setTimeout(calculatePopupPosition, 0)
    } finally {
      setIsRunning(false)
    }
  }

  const handleEdit = () => {
    const code = getCode()
    openCodeEditor(code, language)
  }

  const btnBase = 'flex items-center gap-1 px-2 h-6 text-[11px] rounded transition-all font-medium'

  return (
    <div
      ref={containerRef}
      className="flex items-center gap-1.5 relative"
      onMouseEnter={cancelCloseTimer}
      onMouseLeave={startCloseTimer}
    >
      {(language === 'python' || language === 'javascript' || language === 'js' || language === 'minilang' || language === 'ml' || language === 'mini') && (
        <button
          onClick={handleRun}
          className={`${btnBase} bg-emerald-500/25 text-emerald-300 hover:bg-emerald-500/40 hover:text-emerald-200`}
          title="运行代码"
        >
          <Play size={11} fill="currentColor" />
          {isRunning ? '运行中' : '运行'}
        </button>
      )}
      <button
        onClick={handleEdit}
        className={`${btnBase} bg-blue-500/20 text-blue-300 hover:bg-blue-500/35 hover:text-blue-200`}
        title="在编辑器中打开"
      >
        <Code2 size={11} />
        编辑
      </button>
      <button
        onClick={handleCopy}
        className={`${btnBase} ${copied ? 'bg-green-500/25 text-green-300' : 'bg-white/15 text-gray-200 hover:bg-white/25 hover:text-white'}`}
        title="复制代码"
      >
        {copied ? <Check size={11} /> : <Copy size={11} />}
        {copied ? '已复制' : '复制'}
      </button>
      {runOutput !== null && (
        <button
          onClick={() => setRunOutput(null)}
          className={`${btnBase} bg-white/10 text-gray-400 hover:bg-red-500/20 hover:text-red-300 px-1.5`}
        >
          ×
        </button>
      )}
      {runOutput !== null && (
        createPortal(
          <div
            ref={popupRef}
            className="fixed w-[450px] max-w-[90vw] px-4 py-3 rounded-xl bg-[#1a1b26]/98 backdrop-blur-xl text-xs font-mono text-green-300 max-h-56 overflow-y-auto z-[100] whitespace-pre-wrap shadow-2xl border border-white/10"
            style={{
              ...popupStyle,
              animation: 'fadeInUp 0.15s ease forwards',
            }}
            onClick={(e) => e.stopPropagation()}
            onMouseEnter={cancelCloseTimer}
            onMouseLeave={startCloseTimer}
          >
            <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 font-sans">运行结果</div>
            {runOutput}
          </div>,
          document.body
        )
      )}
    </div>
  )
}

function PreBlock({ children, ...rest }: any) {
  const preRef = useRef<HTMLPreElement>(null)
  const [lang, setLang] = useState('code')

  useEffect(() => {
    if (!preRef.current) return
    const codeEl = preRef.current.querySelector('code')
    if (!codeEl) return
    const langMatch = codeEl.className.match(/language-(\w+)/)
    if (langMatch && langMatch[1]) {
      setLang(langMatch[1])
    }
  }, [])

  const getCode = () => {
    if (!preRef.current) return ''
    const codeEl = preRef.current.querySelector('code')
    return codeEl?.innerText ?? ''
  }

  return (
    <div className="my-4 rounded-xl overflow-hidden bg-[#1e1e2e] shadow-lg relative group/pre">
      <div className="flex items-center justify-between px-3 py-1.5 bg-black/20 border-b border-white/5">
        <span className="text-[10px] text-gray-400 font-mono uppercase tracking-wider">{lang}</span>
        <div className="opacity-0 group-hover/pre:opacity-100 transition-opacity relative">
          <CodeBlockActions language={lang} getCode={getCode} />
        </div>
      </div>
      <pre ref={preRef} className="!my-0 !rounded-none !bg-transparent !shadow-none" {...rest}>
        {children}
      </pre>
    </div>
  )
}

export function MessageBubble({ message, isLast: _isLast, onRegenerate }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'
  const { setExerciseFromChat } = useExercise()
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current)
    }
  }, [])

  const processedContent = useMemo(() => {
    if (isUser) return message.content
    return processContent(message.content)
  }, [message.content, isUser])

  const exerciseInfo = useMemo(() => {
    if (isUser || !message.content || message.generating) return { isExercise: false, question: '' }
    return detectExerciseInContent(message.content)
  }, [message.content, isUser, message.generating])

  const handleCopy = async () => {
    if (!message.content) return
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    if (copyTimerRef.current) clearTimeout(copyTimerRef.current)
    copyTimerRef.current = setTimeout(() => setCopied(false), 2000)
  }

  const handleStartExercise = () => {
    setExerciseFromChat({
      question: exerciseInfo.question,
      starter_code: exerciseInfo.starterCode,
      test_cases: exerciseInfo.testCases,
      exercise_type: exerciseInfo.starterCode ? 'creation' : 'understanding',
      language: exerciseInfo.language,
    })
  }

  const markdownComponents = useMemo(() => ({
    p: ({ children }: any) => <p className="my-2">{children}</p>,
    ul: ({ children }: any) => <ul className="my-3">{children}</ul>,
    ol: ({ children }: any) => <ol className="my-3">{children}</ol>,
    li: ({ children }: any) => <li className="my-1.5">{children}</li>,
    h1: ({ children }: any) => <h1 className="text-xl font-bold mt-6 mb-3 pb-2 border-b-2 border-blue-100">{children}</h1>,
    h2: ({ children }: any) => <h2 className="text-lg font-bold mt-5 mb-2 flex items-center gap-2 before:content-[''] before:w-1 before:h-5 before:bg-gradient-to-b before:from-[#3370ff] before:to-[#5e8bff] before:rounded-sm">{children}</h2>,
    h3: ({ children }: any) => <h3 className="text-base font-semibold mt-4 mb-2">{children}</h3>,
    strong: ({ children }: any) => <strong className="font-semibold text-gray-900">{children}</strong>,
    blockquote: ({ children }: any) => <blockquote className="my-4 pl-4 pr-4 py-3 bg-gradient-to-r from-blue-50/80 to-purple-50/50 border-l-4 border-[#3370ff] rounded-r-lg relative before:content-['❝'] before:absolute before:left-3 before:top-2 before:text-2xl before:text-[#3370ff]/30 before:font-serif">{children}</blockquote>,
    code: ({ className, children, ...props }: any) => {
      const isInline = !className
      if (isInline) {
        return <code className="px-1.5 py-0.5 bg-blue-50 text-[#2860e1] rounded text-[0.9em] font-mono font-medium" {...props}>{children}</code>
      }
      return <code className={className} {...props}>{children}</code>
    },
    pre: PreBlock,
    a: ({ href, children }: any) => <a href={href} className="text-[#3370ff] border-b border-blue-200 hover:border-[#3370ff] transition-colors" target="_blank" rel="noopener noreferrer">{children}</a>,
    table: ({ children }: any) => <div className="my-4 overflow-x-auto rounded-lg border border-gray-200"><table className="w-full text-sm">{children}</table></div>,
    th: ({ children }: any) => <th className="px-4 py-2 bg-blue-50/80 font-semibold text-left border-b border-gray-200">{children}</th>,
    td: ({ children }: any) => <td className="px-4 py-2 border-b border-gray-100">{children}</td>,
    hr: () => <hr className="my-6 border-none h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent" />,
  }), [])

  return (
    <div
      className={cn(
        'flex gap-3 mb-5 animate-in fade-in slide-in-from-bottom-3 duration-300',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      {!isUser && (
        <div className="w-9 h-9 rounded-xl flex-shrink-0 flex items-center justify-center text-sm font-bold shadow-sm bg-white border border-gray-200 text-[#3370ff] mt-0.5">
          C
        </div>
      )}

      <div
        className={cn(
          'max-w-[min(82%,680px)] group relative flex flex-col',
          isUser ? 'items-end' : 'items-start'
        )}
      >
        {isUser ? (
          <div className="px-5 py-3 rounded-2xl rounded-tr-md bg-gradient-to-br from-[#3370ff] to-[#5e8bff] text-white shadow-lg shadow-blue-500/25">
            <p className="whitespace-pre-wrap leading-relaxed text-[15px]">
              {message.content}
            </p>
          </div>
        ) : (
          <div className="w-full">
            <LiquidGlassCard
              className="px-5 py-4 rounded-2xl rounded-tl-md"
              displacementScale={6}
              blur={20}
            >
              <div className="prose prose-chat max-w-none">
                {message.generating && !message.content ? (
                  <div className="flex items-center gap-2 text-gray-400">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-[#3370ff] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-[#3370ff] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-[#3370ff] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-sm">正在思考...</span>
                  </div>
                ) : (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                    components={markdownComponents}
                  >
                    {processedContent}
                  </ReactMarkdown>
                )}
              </div>
            </LiquidGlassCard>

            {exerciseInfo.isExercise && !message.generating && (
              <button
                onClick={handleStartExercise}
                className="mt-2 inline-flex items-center gap-2 px-4 py-2 rounded-xl
                  bg-gradient-to-r from-[#3370ff] to-[#5e8bff] text-white text-sm font-medium
                  shadow-lg shadow-blue-500/20 hover:shadow-xl hover:shadow-blue-500/30
                  hover:-translate-y-0.5 active:translate-y-0 transition-all duration-200"
              >
                <PencilLine size={14} />
                开始交互作答
                <ExternalLink size={12} className="opacity-70" />
              </button>
            )}
          </div>
        )}

        {!isUser && !message.generating && message.content && (
          <div className="flex gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2.5 text-xs text-gray-500 hover:text-gray-700 hover:bg-white/60"
              onClick={handleCopy}
            >
              {copied ? <Check size={13} className="text-green-500" /> : <Copy size={13} />}
              <span className="ml-1">{copied ? '已复制' : '复制'}</span>
            </Button>
            {onRegenerate && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2.5 text-xs text-gray-500 hover:text-gray-700 hover:bg-white/60"
                onClick={onRegenerate}
              >
                <RotateCcw size={13} />
                <span className="ml-1">重新生成</span>
              </Button>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-9 h-9 rounded-xl flex-shrink-0 flex items-center justify-center text-sm font-bold shadow-sm bg-gradient-to-br from-[#3370ff] to-[#5e8bff] text-white mt-0.5">
          你
        </div>
      )}

      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
