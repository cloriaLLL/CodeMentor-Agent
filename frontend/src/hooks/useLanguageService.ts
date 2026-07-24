/**
 * CodeMentor Agent — 编译器语言服务 Hook
 *
 * 提供 IDE 级代码提示的前端状态管理：
 * - 实时诊断（防抖 150ms，避免每次按键都请求）
 * - 自动补全（光标变化时触发）
 * - 悬停提示与签名帮助
 *
 * 复刻项目现有防抖 + AbortController 超时模式（参考 ChatArea 的 45s 超时）。
 *
 * 依据：DOC-05 §4.2 useLanguageService Hook
 */
import { useState, useEffect, useRef, useCallback } from 'react'

/** 诊断信息（与后端 Diagnostic.to_dict 一致） */
export interface Diagnostic {
  line: number
  column: number
  end_column: number | null
  message: string
  severity: 'error' | 'warning' | 'info' | 'hint'
  error_code: string
}

/** 补全候选项 */
export interface CompletionItem {
  label: string
  kind: 'keyword' | 'function' | 'variable' | 'snippet' | 'text'
  detail: string
  insert_text: string
  documentation: string
}

interface LanguageServiceState {
  diagnostics: Diagnostic[]
  error: string | null
}

const LINT_DEBOUNCE_MS = 150
const REQUEST_TIMEOUT_MS = 5000

/**
 * 语言服务 Hook
 * @param code 当前代码
 * @param language 语言名（默认 minilang）
 */
export function useLanguageService(code: string, language: string = 'minilang') {
  const [state, setState] = useState<LanguageServiceState>({
    diagnostics: [],
    error: null,
  })

  const lintAbortRef = useRef<AbortController | null>(null)
  const completeAbortRef = useRef<AbortController | null>(null)
  const lintTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  /** 实时诊断（防抖 150ms） */
  const lint = useCallback(async (source: string) => {
    // 取消上一次未完成的请求
    if (lintAbortRef.current) lintAbortRef.current.abort()
    if (lintTimerRef.current) clearTimeout(lintTimerRef.current)

    lintTimerRef.current = setTimeout(async () => {
      const controller = new AbortController()
      lintAbortRef.current = controller
      const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

      try {
        const resp = await fetch('/api/compiler/lint', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: source, language }),
          signal: controller.signal,
        })
        if (!resp.ok) throw new Error(`lint 失败: ${resp.status}`)
        const data = await resp.json()
        setState((s) => ({ ...s, diagnostics: data.diagnostics || [] }))
      } catch (err) {
        // AbortError 是正常的取消，不报错
        if (err instanceof Error && err.name !== 'AbortError') {
          setState((s) => ({ ...s, error: err.message }))
        }
      } finally {
        clearTimeout(timer)
      }
    }, LINT_DEBOUNCE_MS)
  }, [language])

  /** 自动补全 */
  const complete = useCallback(async (source: string, cursorOffset: number): Promise<CompletionItem[]> => {
    if (completeAbortRef.current) completeAbortRef.current.abort()
    const controller = new AbortController()
    completeAbortRef.current = controller
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

    try {
      const resp = await fetch('/api/compiler/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: source, cursor_offset: cursorOffset, language }),
        signal: controller.signal,
      })
      if (!resp.ok) return []
      const data = await resp.json()
      return data.items || []
    } catch {
      return []
    } finally {
      clearTimeout(timer)
    }
  }, [language])

  /** 悬停提示 */
  const hover = useCallback(async (source: string, offset: number): Promise<string | null> => {
    try {
      const resp = await fetch('/api/compiler/hover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: source, offset, language }),
      })
      if (!resp.ok) return null
      const data = await resp.json()
      return data.result?.content || null
    } catch {
      return null
    }
  }, [language])

  /** 签名帮助 */
  const signatureHelp = useCallback(async (source: string, offset: number) => {
    try {
      const resp = await fetch('/api/compiler/signature', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: source, offset, language }),
      })
      if (!resp.ok) return null
      const data = await resp.json()
      return data.result || null
    } catch {
      return null
    }
  }, [language])

  /** 编译并执行 */
  const compileAndRun = useCallback(async (source: string, run: boolean = true) => {
    try {
      const resp = await fetch('/api/compiler/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: source, language, target: 'python', run }),
      })
      if (!resp.ok) throw new Error(`编译失败: ${resp.status}`)
      return await resp.json()
    } catch (err) {
      return { status: 'error', error: err instanceof Error ? err.message : '编译失败' }
    }
  }, [language])

  // code 变化时自动触发诊断（防抖）
  useEffect(() => {
    lint(code)
    return () => {
      if (lintTimerRef.current) clearTimeout(lintTimerRef.current)
      if (lintAbortRef.current) lintAbortRef.current.abort()
    }
  }, [code, lint])

  return {
    diagnostics: state.diagnostics,
    error: state.error,
    lint,
    complete,
    hover,
    signatureHelp,
    compileAndRun,
  }
}
