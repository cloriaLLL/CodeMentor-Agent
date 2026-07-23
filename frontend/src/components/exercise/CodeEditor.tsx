import { useRef, useEffect, useCallback, useState } from 'react'
import hljs from 'highlight.js'
import { useLanguageService, type CompletionItem, type Diagnostic } from '../../hooks/useLanguageService'
import { DiagnosticsLayer } from './DiagnosticsLayer'
import { CompletionPopup } from './CompletionPopup'

interface CodeEditorProps {
  value: string
  onChange: (value: string) => void
  language?: string
  placeholder?: string
  minHeight?: number
  disabled?: boolean
  /** 是否启用编译器 IDE 提示（语法高亮始终启用） */
  enableLanguageService?: boolean
  /** 编译器语言名（用于 IDE 提示，默认 minilang） */
  compilerLanguage?: string
}

const BRACKET_PAIRS: Record<string, string> = {
  '(': ')',
  '[': ']',
  '{': '}',
}
const CLOSING_BRACKETS = new Set([')', ']', '}'])

export function CodeEditor({
  value,
  onChange,
  language = 'python',
  placeholder = '在此编写代码...',
  minHeight = 240,
  disabled = false,
  enableLanguageService = false,
  compilerLanguage = 'minilang',
}: CodeEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const highlightRef = useRef<HTMLPreElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // IDE 语言服务（仅在启用时初始化）
  const isMiniLang = enableLanguageService || language === 'minilang' || language === 'ml'
  const langService = useLanguageService(
    isMiniLang ? value : '',
    compilerLanguage,
  )

  // 补全弹窗状态
  const [completionItems, setCompletionItems] = useState<CompletionItem[]>([])
  const [completionVisible, setCompletionVisible] = useState(false)
  const [completionIndex, setCompletionIndex] = useState(0)
  const [popupPosition, setPopupPosition] = useState({ top: 0, left: 0 })
  const completeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const blurTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // textarea 滚动位移（用于诊断层同步滚动）
  const [scrollOffset, setScrollOffset] = useState({ top: 0, left: 0 })

  // 卸载时清理所有定时器，避免 setState after unmount
  useEffect(() => {
    return () => {
      if (completeTimerRef.current) clearTimeout(completeTimerRef.current)
      if (blurTimerRef.current) clearTimeout(blurTimerRef.current)
    }
  }, [])

  const highlight = useCallback(() => {
    if (!highlightRef.current) return
    const code = value || ''
    let html: string
    // MiniLang 使用自定义高亮（fallback 到 python 语法近似）
    const hlLang = isMiniLang ? 'python' : language
    if (code && hljs.getLanguage(hlLang)) {
      try {
        html = hljs.highlight(code, { language: hlLang }).value
      } catch {
        html = escapeHtml(code)
      }
    } else {
      html = escapeHtml(code)
    }
    if (code.endsWith('\n') || code === '') {
      html += '\n'
    }
    highlightRef.current.innerHTML = html
  }, [value, language, isMiniLang])

  useEffect(() => {
    highlight()
  }, [highlight])

  const syncScroll = useCallback(() => {
    const ta = textareaRef.current
    const pre = highlightRef.current
    if (!ta || !pre) return
    pre.scrollTop = ta.scrollTop
    pre.scrollLeft = ta.scrollLeft
    // 同步诊断层滚动位移
    setScrollOffset({ top: ta.scrollTop, left: ta.scrollLeft })
  }, [])

  // 计算光标像素位置（用于补全弹窗定位）
  const getCursorPixelPosition = useCallback(() => {
    const ta = textareaRef.current
    if (!ta) return { top: 0, left: 0 }
    const { selectionStart } = ta
    const before = value.slice(0, selectionStart)
    const lines = before.split('\n')
    const line = lines.length
    const col = lines[lines.length - 1].length + 1
    const fontSize = 13
    const lineHeight = 20.8
    const padding = 16   // 与 textarea 的 p-4 一致
    return {
      // 加 padding、减滚动位移，确保弹窗随光标正确定位
      top: (line - 1) * lineHeight + padding - ta.scrollTop + lineHeight,
      left: (col - 1) * fontSize * 0.6 + padding - ta.scrollLeft,
    }
  }, [value])

  // 触发自动补全
  const triggerCompletion = useCallback((cursorOffset: number) => {
    if (!isMiniLang) return
    if (completeTimerRef.current) clearTimeout(completeTimerRef.current)
    completeTimerRef.current = setTimeout(async () => {
      const items = await langService.complete(value, cursorOffset)
      if (items.length > 0) {
        setCompletionItems(items)
        setCompletionIndex(0)
        setCompletionVisible(true)
        setPopupPosition(getCursorPixelPosition())
      } else {
        setCompletionVisible(false)
      }
    }, 200)
  }, [isMiniLang, langService, value, getCursorPixelPosition])

  // 插入补全项
  const insertCompletion = useCallback((item: CompletionItem) => {
    const ta = textareaRef.current
    if (!ta) return
    const { selectionStart: start, selectionEnd: end } = ta
    // 处理光标占位符 $1
    let insertText = item.insert_text || item.label
    let cursorOffset = insertText.length
    const placeholderMatch = insertText.match(/\$(\d+)/)
    if (placeholderMatch) {
      cursorOffset = insertText.indexOf('$')
      insertText = insertText.replace(/\$\d+/, '')
    }
    const newValue = value.slice(0, start) + insertText + value.slice(end)
    onChange(newValue)
    setCompletionVisible(false)
    requestAnimationFrame(() => {
      if (ta) {
        ta.selectionStart = ta.selectionEnd = start + cursorOffset
        ta.focus()
      }
    })
  }, [value, onChange])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const ta = e.currentTarget
    const { selectionStart: start, selectionEnd: end } = ta

    // 补全弹窗打开时，导航键交给 CodeEditor 统一处理（避免 CompletionPopup 与此处双触发）
    if (completionVisible) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setCompletionIndex((completionIndex + 1) % completionItems.length)
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setCompletionIndex((completionIndex - 1 + completionItems.length) % completionItems.length)
        return
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        setCompletionVisible(false)
        return
      }
      if (e.key === 'Enter') {
        e.preventDefault()
        e.stopPropagation()   // 阻止冒泡，防止 CompletionPopup 再次处理导致双插入
        insertCompletion(completionItems[completionIndex])
        return
      }
    }

    if (e.key === 'Enter') {
      e.preventDefault()
      const before = ta.value.slice(0, start)
      const lineStart = before.lastIndexOf('\n') + 1
      const currentLine = before.slice(lineStart)
      const indentMatch = currentLine.match(/^\s*/)
      const indent = indentMatch ? indentMatch[0] : ''
      const lastChar = before.slice(-1)
      const nextChar = ta.value.slice(start, start + 1)
      let insert = '\n' + indent
      let caretOffset = indent.length

      if (lastChar === ':' || lastChar === '{' || lastChar === '[' || lastChar === '(') {
        insert += '  '
        caretOffset += 2
      }

      if (BRACKET_PAIRS[lastChar] && nextChar === BRACKET_PAIRS[lastChar]) {
        insert = '\n' + indent + '  ' + '\n' + indent
        caretOffset = indent.length + 2
      }

      const newValue = ta.value.slice(0, start) + insert + ta.value.slice(end)
      onChange(newValue)
      requestAnimationFrame(() => {
        ta.selectionStart = ta.selectionEnd = start + caretOffset + 1
      })
      return
    }

    if (BRACKET_PAIRS[e.key]) {
      const nextChar = ta.value.slice(start, start + 1)
      if (nextChar === BRACKET_PAIRS[e.key] && start === end) {
        e.preventDefault()
        const newValue = ta.value.slice(0, start) + e.key + ta.value.slice(end + 1)
        onChange(newValue)
        requestAnimationFrame(() => {
          ta.selectionStart = ta.selectionEnd = start + 1
        })
        return
      }
      if (start === end) {
        e.preventDefault()
        const closing = BRACKET_PAIRS[e.key]
        const newValue = ta.value.slice(0, start) + e.key + closing + ta.value.slice(end)
        onChange(newValue)
        requestAnimationFrame(() => {
          ta.selectionStart = ta.selectionEnd = start + 1
        })
        return
      }
    }

    if (CLOSING_BRACKETS.has(e.key) && start === end) {
      const nextChar = ta.value.slice(start, start + 1)
      if (nextChar === e.key) {
        e.preventDefault()
        const newValue = ta.value.slice(0, start) + ta.value.slice(end + 1)
        onChange(newValue)
        requestAnimationFrame(() => {
          ta.selectionStart = ta.selectionEnd = start
        })
        return
      }
    }

    if (e.key === 'Tab') {
      e.preventDefault()
      if (start === end) {
        const newValue = ta.value.slice(0, start) + '  ' + ta.value.slice(end)
        onChange(newValue)
        requestAnimationFrame(() => {
          ta.selectionStart = ta.selectionEnd = start + 2
        })
      }
    }

    if (e.key === '"' || e.key === "'") {
      if (start === end) {
        e.preventDefault()
        const quote = e.key
        const newValue = ta.value.slice(0, start) + quote + quote + ta.value.slice(end)
        onChange(newValue)
        requestAnimationFrame(() => {
          ta.selectionStart = ta.selectionEnd = start + 1
        })
      }
    }

    // Ctrl+Space 手动触发补全
    if (e.ctrlKey && e.key === ' ') {
      e.preventDefault()
      triggerCompletion(start)
    }
  }, [onChange, completionVisible, completionItems, completionIndex, insertCompletion, triggerCompletion])

  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value)
    syncScroll()
    // 输入时自动触发补全
    if (isMiniLang) {
      const offset = e.target.selectionStart
      // 检查光标前字符是否为标识符字符
      const char = e.target.value[offset - 1]
      if (char && (/[a-zA-Z_]/.test(char))) {
        triggerCompletion(offset)
      } else {
        setCompletionVisible(false)
      }
    }
  }, [onChange, syncScroll, isMiniLang, triggerCompletion])

  const handleBlur = useCallback(() => {
    // 延迟关闭弹窗，允许点击选中（用 ref 存定时器，卸载时可清理）
    blurTimerRef.current = setTimeout(() => setCompletionVisible(false), 150)
  }, [])

  return (
    <div
      ref={containerRef}
      className="relative rounded-xl overflow-hidden border border-gray-200/80 bg-[#1e1e2e] shadow-inner"
      style={{ minHeight }}
    >
      <pre
        ref={highlightRef}
        aria-hidden="true"
        className="absolute inset-0 m-0 p-4 font-mono text-[13px] leading-[1.6] overflow-auto pointer-events-none whitespace-pre"
        style={{ color: '#cdd6f4' }}
      />
      {/* 诊断下划线层（仅 MiniLang 启用） */}
      {isMiniLang && (
        <DiagnosticsLayer
          diagnostics={langService.diagnostics}
          scrollTop={scrollOffset.top}
          scrollLeft={scrollOffset.left}
        />
      )}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleInput}
        onScroll={syncScroll}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        placeholder={placeholder}
        spellCheck={false}
        disabled={disabled}
        className="absolute inset-0 w-full h-full p-4 font-mono text-[13px] leading-[1.6] bg-transparent text-transparent caret-white resize-none outline-none whitespace-pre overflow-auto"
        style={{
          caretColor: '#ffffff',
          WebkitTextFillColor: 'transparent',
        }}
      />
      {/* 补全弹窗（仅 MiniLang 启用） */}
      {isMiniLang && (
        <CompletionPopup
          items={completionItems}
          selectedIndex={completionIndex}
          onSelectIndex={setCompletionIndex}
          onConfirm={insertCompletion}
          onCancel={() => setCompletionVisible(false)}
          position={popupPosition}
          visible={completionVisible}
        />
      )}
    </div>
  )
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
