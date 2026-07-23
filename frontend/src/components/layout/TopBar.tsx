import { useState, useRef, useEffect } from 'react'
import { Menu, ChevronDown, MoreVertical, Plus, Pencil, Trash2, BookOpen } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LiquidGlassCard } from '@/components/ui/liquid-glass-card'
import { useChat } from '@/contexts/ChatContext'
import { cn } from '@/lib/utils'

export function TopBar() {
  const {
    sidebarOpen,
    dispatch,
    getCurrentChat,
    modelList,
    currentModel,
    isGenerating,
  } = useChat()
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const modelRef = useRef<HTMLDivElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  const currentChat = getCurrentChat()
  const currentModelName = modelList.find(m => m.id === currentModel)?.name ?? '选择模型'

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modelRef.current && !modelRef.current.contains(e.target as Node)) {
        setModelDropdownOpen(false)
      }
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleClearAll = () => {
    if (confirm('确定要清空所有对话和笔记本吗？此操作不可恢复。')) {
      localStorage.removeItem('codementor_data')
      window.location.reload()
    }
  }

  return (
    <header className="flex-shrink-0 h-14 px-4 flex items-center justify-between relative z-30">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            'h-9 w-9 liquid-glass-base rounded-lg',
            sidebarOpen ? 'hidden md:hidden' : 'flex'
          )}
          onClick={() => dispatch({ type: 'TOGGLE_SIDEBAR' })}
        >
          <Menu size={18} />
        </Button>
        <h1 className="font-semibold text-base truncate max-w-[200px] md:max-w-none">
          {currentChat?.title ?? 'CodeMentor'}
        </h1>
      </div>

      <div className="flex items-center gap-2">
        <div ref={modelRef} className="relative">
          <button
            className="h-9 px-3 flex items-center gap-1.5 text-sm rounded-lg liquid-glass-base hover:bg-white/90 transition-all"
            onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
            disabled={isGenerating}
          >
            <span className="truncate max-w-[120px]">{currentModelName}</span>
            <ChevronDown size={14} className={cn('transition-transform', modelDropdownOpen && 'rotate-180')} />
          </button>
          {modelDropdownOpen && (
            <LiquidGlassCard
              className="absolute right-0 top-full mt-1 w-56 py-1 z-50"
              displacementScale={8}
            >
              {modelList.map(model => (
                <button
                  key={model.id}
                  className={cn(
                    'w-full px-3 py-2 text-left text-sm flex items-center justify-between hover:bg-black/5 transition-colors',
                    currentModel === model.id && 'text-[#3370ff] bg-[#3370ff]/5'
                  )}
                  onClick={() => {
                    dispatch({ type: 'SET_CURRENT_MODEL', payload: model.id })
                    setModelDropdownOpen(false)
                  }}
                >
                  {model.name}
                  {currentModel === model.id && (
                    <div className="w-2 h-2 rounded-full bg-[#3370ff]" />
                  )}
                </button>
              ))}
            </LiquidGlassCard>
          )}
        </div>

        <div ref={menuRef} className="relative">
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            <MoreVertical size={18} />
          </Button>
          {menuOpen && (
            <LiquidGlassCard
              className="absolute right-0 top-full mt-1 w-48 py-1 z-50"
              displacementScale={8}
            >
              <button
                className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-black/5 transition-colors"
                onClick={() => {
                  dispatch({ type: 'NEW_CHAT', payload: 'chat' })
                  setMenuOpen(false)
                }}
              >
                <Plus size={14} />
                新建对话
              </button>
              <button
                className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-black/5 transition-colors"
                onClick={() => {
                  dispatch({ type: 'NEW_CHAT', payload: 'notebook' })
                  setMenuOpen(false)
                }}
              >
                <BookOpen size={14} />
                新建笔记本
              </button>
              {currentChat && (
                <button
                  className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-black/5 transition-colors"
                  onClick={() => {
                    const newTitle = prompt('请输入新名称', currentChat.title)
                    if (newTitle?.trim()) {
                      dispatch({
                        type: 'RENAME_CHAT',
                        payload: { id: currentChat.id, title: newTitle.trim() },
                      })
                    }
                    setMenuOpen(false)
                  }}
                >
                  <Pencil size={14} />
                  重命名当前
                </button>
              )}
              <div className="h-px bg-black/5 my-1" />
              <button
                className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 text-red-500 hover:bg-red-50 transition-colors"
                onClick={() => {
                  handleClearAll()
                  setMenuOpen(false)
                }}
              >
                <Trash2 size={14} />
                清空所有数据
              </button>
            </LiquidGlassCard>
          )}
        </div>
      </div>
    </header>
  )
}
