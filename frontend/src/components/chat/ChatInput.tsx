import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Square, GripHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LiquidGlassCard } from '@/components/ui/liquid-glass-card'
import { useChat } from '@/contexts/ChatContext'
import { useExercise } from '@/contexts/ExerciseContext'
import { detectExerciseRequest } from '@/hooks/useExerciseLauncher'

const MIN_HEIGHT = 44
const MAX_HEIGHT = 300
const DEFAULT_HEIGHT = 44

export function ChatInput() {
  const { sendMessage, stopGeneration, isGenerating, getCurrentChat } = useChat()
  const { generateExercise } = useExercise()
  const [input, setInput] = useState('')
  const [textareaHeight, setTextareaHeight] = useState(DEFAULT_HEIGHT)
  const [isDragging, setIsDragging] = useState(false)
  const [showResizeHint, setShowResizeHint] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const dragStartYRef = useRef(0)
  const dragStartHeightRef = useRef(0)

  const currentChat = getCurrentChat()
  const isNotebook = currentChat?.type === 'notebook'

  const autoResize = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    const scrollHeight = el.scrollHeight
    const newHeight = Math.min(Math.max(scrollHeight, MIN_HEIGHT), MAX_HEIGHT)
    el.style.height = newHeight + 'px'
    if (!isDragging) {
      setTextareaHeight(newHeight)
    }
  }, [isDragging])

  useEffect(() => {
    autoResize()
  }, [input, autoResize])

  useEffect(() => {
    if (isDragging) {
      document.body.style.cursor = 'ns-resize'
      document.body.style.userSelect = 'none'
    } else {
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    return () => {
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isDragging])

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)
    dragStartYRef.current = e.clientY
    dragStartHeightRef.current = textareaHeight
  }

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      const deltaY = dragStartYRef.current - e.clientY
      const newHeight = Math.min(
        Math.max(dragStartHeightRef.current + deltaY, MIN_HEIGHT),
        MAX_HEIGHT
      )
      setTextareaHeight(newHeight)
      if (textareaRef.current) {
        textareaRef.current.style.height = newHeight + 'px'
      }
    }

    const handleMouseUp = () => {
      setIsDragging(false)
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, textareaHeight])

  const handleSubmit = () => {
    if (!input.trim() || isGenerating) return
    const trimmedInput = input.trim()

    const exerciseReq = detectExerciseRequest(trimmedInput)
    if (exerciseReq) {
      generateExercise(exerciseReq)
      setInput('')
      setTextareaHeight(DEFAULT_HEIGHT)
      if (textareaRef.current) {
        textareaRef.current.style.height = DEFAULT_HEIGHT + 'px'
      }
      return
    }

    sendMessage(trimmedInput)
    setInput('')
    setTextareaHeight(DEFAULT_HEIGHT)
    if (textareaRef.current) {
      textareaRef.current.style.height = DEFAULT_HEIGHT + 'px'
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex-shrink-0 p-4 pb-5">
      <div className="max-w-3xl mx-auto relative">
        <LiquidGlassCard className="overflow-hidden relative" displacementScale={12}>
          <div
            className="absolute top-0 left-0 right-0 h-2 cursor-ns-resize z-10 flex items-start justify-center group"
            onMouseDown={handleMouseDown}
            onMouseEnter={() => setShowResizeHint(true)}
            onMouseLeave={() => !isDragging && setShowResizeHint(false)}
          >
            <div
              className={`mt-0.5 transition-all duration-200 ${
                isDragging || showResizeHint ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'
              }`}
            >
              <GripHorizontal size={14} className="text-gray-400" />
            </div>
          </div>

          {(isDragging || showResizeHint) && (
            <div className="absolute -top-7 left-1/2 -translate-x-1/2 px-2 py-1 bg-gray-800 text-white text-xs rounded shadow-lg z-20 whitespace-nowrap pointer-events-none">
              {Math.round(textareaHeight)}px
            </div>
          )}

          <div className="flex items-end gap-2 p-2 pt-3">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isNotebook ? '在笔记本中记录你的想法...' : '和我聊聊吧...'}
              rows={1}
              style={{
                height: textareaHeight,
                scrollbarWidth: 'none',
                msOverflowStyle: 'none',
              }}
              className="flex-1 bg-transparent border-none outline-none resize-none px-3 py-2 text-[15px] leading-relaxed placeholder:text-gray-400 overflow-y-auto"
              disabled={isGenerating}
            />
            {isGenerating ? (
              <Button
                variant="outline"
                size="icon"
                className="h-9 w-9 rounded-full flex-shrink-0"
                onClick={stopGeneration}
              >
                <Square size={16} fill="currentColor" />
              </Button>
            ) : (
              <Button
                variant="primary"
                size="icon"
                className="h-9 w-9 rounded-full flex-shrink-0"
                onClick={handleSubmit}
                disabled={!input.trim()}
              >
                <Send size={16} />
              </Button>
            )}
          </div>
        </LiquidGlassCard>
        <div className="text-center mt-2 text-xs text-gray-400">
          按 Enter 发送，Shift+Enter 换行 · 拖拽顶部边框调节高度 · 对话自动保存
        </div>
      </div>
      <style>{`
        textarea::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  )
}
