/**
 * CodeMentor Agent — 自动补全弹窗
 *
 * 显示补全候选列表，支持键盘导航（↑↓选择、Enter确认、Esc取消）。
 * 定位在光标处，跟随光标移动。
 *
 * 设计：纯展示组件。键盘事件由 CodeEditor 统一处理（避免双插入），
 * 本组件仅负责渲染与鼠标交互。
 *
 * 依据：DOC-05 §4.2 自动补全
 */
import { useEffect, useRef } from 'react'
import type { CompletionItem } from '../../hooks/useLanguageService'

interface CompletionPopupProps {
  /** 补全候选 */
  items: CompletionItem[]
  /** 当前选中索引 */
  selectedIndex: number
  /** 选中索引变化回调 */
  onSelectIndex: (index: number) => void
  /** 确认选择回调 */
  onConfirm: (item: CompletionItem) => void
  /** 取消回调（Esc） */
  onCancel: () => void
  /** 弹窗位置（相对于编辑器容器） */
  position: { top: number; left: number }
  /** 是否显示 */
  visible: boolean
}

const KIND_ICON: Record<string, string> = {
  keyword: '🔑',
  function: 'ƒ',
  variable: 'x',
  snippet: '~',
  text: 'T',
}

const KIND_COLOR: Record<string, string> = {
  keyword: '#cba6f7',
  function: '#89b4fa',
  variable: '#a6e3a1',
  snippet: '#f9e2af',
  text: '#cdd6f4',
}

export function CompletionPopup({
  items,
  selectedIndex,
  onSelectIndex,
  onConfirm,
  onCancel,
  position,
  visible,
}: CompletionPopupProps) {
  const listRef = useRef<HTMLDivElement>(null)
  // 用 ref 存最新值，供不依赖具体值的 effect 读取
  const stateRef = useRef({ selectedIndex: 0, items: [] as CompletionItem[] })
  stateRef.current = { selectedIndex, items }

  // 选中项滚动到可视区（仅滚动弹窗自身，不影响外层）
  useEffect(() => {
    if (!visible || !listRef.current) return
    const selected = listRef.current.children[selectedIndex] as HTMLElement
    if (selected) {
      const popup = listRef.current
      const top = selected.offsetTop - popup.offsetTop
      const bottom = top + selected.offsetHeight
      if (top < popup.scrollTop) {
        popup.scrollTop = top
      } else if (bottom > popup.scrollTop + popup.clientHeight) {
        popup.scrollTop = bottom - popup.clientHeight
      }
    }
  }, [selectedIndex, visible])

  // Esc 键取消（仅监听 Esc，Enter/Arrow 交给 CodeEditor 避免双触发）
  useEffect(() => {
    if (!visible) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onCancel()
      }
    }
    window.addEventListener('keydown', handleKey, true)
    return () => window.removeEventListener('keydown', handleKey, true)
  }, [visible, onCancel])

  if (!visible || items.length === 0) return null

  return (
    <div
      role="listbox"
      aria-label="补全候选"
      className="absolute z-50 max-h-64 w-72 overflow-auto rounded-lg border border-gray-600/60 bg-[#1e1e2e] shadow-2xl"
      style={{ top: position.top, left: position.left }}
      ref={listRef}
    >
      {items.map((item, idx) => {
        const icon = KIND_ICON[item.kind] || 'T'
        const color = KIND_COLOR[item.kind] || '#cdd6f4'
        return (
          <div
            key={`${item.label}:${item.insert_text}:${idx}`}
            role="option"
            aria-selected={idx === selectedIndex}
            className={`flex cursor-pointer items-center gap-2 px-3 py-1.5 text-[13px] font-mono ${
              idx === selectedIndex
                ? 'bg-[#313244] text-white'
                : 'text-gray-300 hover:bg-[#313244]/50'
            }`}
            onMouseEnter={() => onSelectIndex(idx)}
            onClick={() => onConfirm(item)}
          >
            <span style={{ color }} className="w-4 text-center">
              {icon}
            </span>
            <span className="flex-1">{item.label}</span>
            {item.detail && (
              <span className="text-[10px] text-gray-500">{item.detail}</span>
            )}
          </div>
        )
      })}
    </div>
  )
}
