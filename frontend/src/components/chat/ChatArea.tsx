import { useRef, useEffect, useState, useCallback } from 'react'
import { ChevronDown, MessageSquare } from 'lucide-react'
import { MessageBubble } from './MessageBubble'
import { WelcomeScreen } from './WelcomeScreen'
import { ExerciseLauncher } from '@/components/exercise/ExerciseLauncher'
import { LiquidGlassCard } from '@/components/ui/liquid-glass-card'
import { useChat } from '@/contexts/ChatContext'
import { cn } from '@/lib/utils'

export function ChatArea() {
  const { getCurrentMessages, isGenerating } = useChat()
  const messages = getCurrentMessages()
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const messageRefs = useRef<Map<string, HTMLDivElement>>(new Map())
  const autoScrollEnabled = useRef(true)
  const isUserScrolling = useRef(false)
  const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [showScrollButton, setShowScrollButton] = useState(false)
  const [showNav, setShowNav] = useState(false)
  const [activeMessageIndex, setActiveMessageIndex] = useState(-1)

  const sortedMessages = [...messages].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  )

  const isEmpty = sortedMessages.length === 0

  const isAtBottom = useCallback((el: HTMLElement) => {
    const threshold = 80
    return el.scrollHeight - el.scrollTop - el.clientHeight < threshold
  }, [])

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior })
    }
    autoScrollEnabled.current = true
    setShowScrollButton(false)
  }, [])

  const handleScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return

    const atBottomNow = isAtBottom(el)

    if (atBottomNow) {
      autoScrollEnabled.current = true
      setShowScrollButton(false)
    } else {
      autoScrollEnabled.current = false
      setShowScrollButton(isGenerating || sortedMessages.length > 0)
    }

    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current)
    }
    isUserScrolling.current = true
    scrollTimeoutRef.current = setTimeout(() => {
      isUserScrolling.current = false
    }, 150)

    let closestIdx = -1
    let closestDist = Infinity
    messageRefs.current.forEach((el, id) => {
      const rect = el.getBoundingClientRect()
      const containerRect = scrollRef.current!.getBoundingClientRect()
      const dist = Math.abs(rect.top - containerRect.top - 60)
      if (dist < closestDist && rect.top < containerRect.bottom) {
        closestDist = dist
        closestIdx = sortedMessages.findIndex(m => m.id === id)
      }
    })
    setActiveMessageIndex(closestIdx)
  }, [isAtBottom, isGenerating, sortedMessages])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.addEventListener('scroll', handleScroll, { passive: true })
    return () => {
      el.removeEventListener('scroll', handleScroll)
      if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current)
    }
  }, [handleScroll])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return

    if (autoScrollEnabled.current) {
      bottomRef.current?.scrollIntoView({ behavior: isGenerating ? 'auto' : 'smooth' })
    }
  }, [messages, isGenerating])

  useEffect(() => {
    if (isGenerating) {
      const el = scrollRef.current
      if (el && isAtBottom(el)) {
        autoScrollEnabled.current = true
        setShowScrollButton(false)
      }
    } else {
      autoScrollEnabled.current = true
      setShowScrollButton(false)
    }
  }, [isGenerating, isAtBottom])

  const scrollToMessage = useCallback((index: number) => {
    const msg = sortedMessages[index]
    if (!msg) return
    const el = messageRefs.current.get(msg.id)
    if (el && scrollRef.current) {
      autoScrollEnabled.current = false
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [sortedMessages])

  const registerMessageRef = useCallback((id: string, el: HTMLDivElement | null) => {
    if (el) {
      messageRefs.current.set(id, el)
    } else {
      messageRefs.current.delete(id)
    }
  }, [])

  const jumpNavItems = sortedMessages
    .map((msg, idx) => ({ msg, idx }))
    .filter(({ msg }) => msg.role === 'user')

  return (
    <div className="flex-1 flex flex-col overflow-hidden relative">
      <div className="absolute top-3 right-3 z-20">
        <ExerciseLauncher />
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-smooth">
        {isEmpty ? (
          <WelcomeScreen />
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6">
            {sortedMessages.map((msg, index) => (
              <div key={msg.id} ref={el => registerMessageRef(msg.id, el)}>
                <MessageBubble
                  message={msg}
                  isLast={index === sortedMessages.length - 1}
                />
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {showScrollButton && (
        <button
          onClick={() => scrollToBottom('smooth')}
          className={cn(
            'absolute bottom-4 left-1/2 -translate-x-1/2 z-20',
            'flex items-center gap-1.5 px-3.5 h-9 rounded-full liquid-glass-base',
            'text-sm text-gray-600 hover:text-[#3370ff]',
            'transition-all duration-200 animate-in fade-in slide-in-from-bottom-2',
            'hover:shadow-[0_12px_40px_rgba(0,0,0,0.08)] hover:-translate-y-0.5'
          )}
        >
          <ChevronDown size={16} />
          {isGenerating && <span className="text-xs">新内容</span>}
        </button>
      )}

      {!isEmpty && (
        <>
          <button
            onClick={() => setShowNav(v => !v)}
            className={cn(
              'absolute right-3 bottom-20 z-20',
              'w-9 h-9 rounded-full flex items-center justify-center liquid-glass-base',
              'text-gray-500 hover:text-[#3370ff]',
              'hover:shadow-[0_8px_24px_rgba(0,0,0,0.08)] transition-all duration-200',
              showNav && 'text-[#3370ff] bg-blue-50/70'
            )}
            title="对话定位"
          >
            <MessageSquare size={16} />
          </button>

          {showNav && (
            <div
              className="absolute right-16 bottom-20 z-30"
              style={{ animation: 'fadeInUp 0.15s ease forwards' }}
            >
              <LiquidGlassCard
                displacementScale={8}
                blur={16}
                className="rounded-2xl py-2 px-2 w-[220px] max-h-[50vh] overflow-y-auto"
              >
                <div className="text-[10px] text-gray-400 px-2 py-1 font-medium uppercase tracking-wider">
                  对话导航
                </div>
                {jumpNavItems.map(({ msg, idx }, navIdx) => {
                  const preview = msg.content.slice(0, 20).replace(/\n/g, ' ')
                  const nextNavIdx = navIdx < jumpNavItems.length - 1 ? jumpNavItems[navIdx + 1].idx : sortedMessages.length
                  const isActive = activeMessageIndex >= idx && activeMessageIndex < nextNavIdx
                  return (
                    <button
                      key={msg.id}
                      onClick={() => scrollToMessage(idx)}
                      className={cn(
                        'w-full text-left px-2 py-1.5 rounded-lg text-xs flex items-center gap-2 transition-colors',
                        'hover:bg-blue-50/80 text-gray-500 hover:text-[#3370ff]',
                        isActive && 'bg-blue-50/80 text-[#3370ff] font-medium'
                      )}
                    >
                      <span className={cn(
                        'w-1.5 h-1.5 rounded-full flex-shrink-0',
                        isActive ? 'bg-[#3370ff]' : 'bg-gray-300'
                      )} />
                      <span className="truncate">{preview}{msg.content.length > 20 ? '…' : ''}</span>
                    </button>
                  )
                })}
              </LiquidGlassCard>
            </div>
          )}
        </>
      )}

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-50%) scale(0.96); }
          to { opacity: 1; transform: translateY(-50%) scale(1); }
        }
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(8px) scale(0.96); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
      `}</style>
    </div>
  )
}
