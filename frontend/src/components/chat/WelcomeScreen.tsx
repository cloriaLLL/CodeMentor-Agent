import { Code, BookOpen, Zap, Terminal, Database, MessageSquare } from 'lucide-react'
import { LiquidGlassCard } from '@/components/ui/liquid-glass-card'
import { useChat } from '@/contexts/ChatContext'
import { useState, useEffect } from 'react'

const quickActions = [
  { icon: Code, label: '学习 Python', prompt: '我想零基础开始学习Python，请从最基础开始教我' },
  { icon: Terminal, label: '学习 JavaScript', prompt: '我想学习JavaScript前端开发，请从零开始带我入门' },
  { icon: Zap, label: '学习 React', prompt: '我想学习React框架，我已经掌握HTML/CSS/JS基础' },
  { icon: Database, label: '学习 FastAPI', prompt: '我想学习FastAPI后端开发，请从环境搭建开始教我' },
]

export function WelcomeScreen() {
  const { sendMessage, dispatch, currentView } = useChat()
  const [showNotebookConfirm, setShowNotebookConfirm] = useState(false)
  const [pendingNotebookPrompt, setPendingNotebookPrompt] = useState<string | null>(null)

  useEffect(() => {
    if (currentView === 'notebooks') {
      dispatch({ type: 'SET_VIEW', payload: 'chats' })
    }
  }, [])

  const handleQuickAction = (prompt: string, forceNotebook?: boolean) => {
    if (forceNotebook) {
      setPendingNotebookPrompt(prompt)
      setShowNotebookConfirm(true)
    } else {
      sendMessage(prompt)
    }
  }

  const confirmCreateNotebook = () => {
    if (pendingNotebookPrompt) {
      dispatch({ type: 'NEW_CHAT', payload: 'notebook' })
      setTimeout(() => sendMessage(pendingNotebookPrompt), 150)
    } else {
      dispatch({ type: 'NEW_CHAT', payload: 'notebook' })
    }
    setShowNotebookConfirm(false)
    setPendingNotebookPrompt(null)
  }

  const handleNewChat = () => {
    dispatch({ type: 'NEW_CHAT', payload: 'chat' })
  }

  const handleNewNotebook = () => {
    setPendingNotebookPrompt(null)
    setShowNotebookConfirm(true)
  }

  return (
    <>
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-8 text-center overflow-y-auto">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#3370ff] to-[#5e8bff] flex items-center justify-center text-white text-3xl font-bold mb-5 shadow-xl shadow-blue-500/30">
          C
        </div>
        <h2 className="text-[clamp(1.5rem,3vw,2rem)] font-bold mb-2 bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
          你好，我是 CodeMentor
        </h2>
        <p className="text-gray-500 mb-8 max-w-md leading-relaxed text-[15px]">
          你的专属编程学习导师。我会带你从零开始系统学习编程，
          每个知识点都会详细讲解原理、给出代码示例，并根据你的节奏动态调整。
        </p>

        <div className="w-full max-w-2xl">
          <div className="flex justify-center gap-3 mb-6">
            <button
              onClick={handleNewChat}
              className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#3370ff] text-white text-sm font-medium hover:bg-[#2860e6] transition-all hover:scale-105 shadow-lg shadow-blue-500/20"
            >
              <MessageSquare size={16} />
              开始对话
            </button>
            <button
              onClick={handleNewNotebook}
              className="flex items-center gap-2 px-5 py-2.5 rounded-full liquid-glass-base text-gray-700 text-sm font-medium hover:text-[#3370ff] transition-all hover:scale-105"
            >
              <BookOpen size={16} />
              新建笔记本
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
            {quickActions.map((action, i) => {
              const Icon = action.icon
              return (
                <LiquidGlassCard
                  key={i}
                  className="p-4 cursor-pointer hover:scale-[1.02] transition-all duration-200"
                  onClick={() => handleQuickAction(action.prompt)}
                  displacementScale={8}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500/10 to-purple-500/10 flex items-center justify-center text-[#3370ff]">
                      <Icon size={18} />
                    </div>
                    <span className="text-sm font-medium text-gray-700">
                      {action.label}
                    </span>
                  </div>
                </LiquidGlassCard>
              )
            })}
          </div>

          <p className="text-xs text-gray-400">
            提示：按 <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">Ctrl</kbd> + <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">N</kbd> 新建对话，
            按 <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">Ctrl</kbd> + <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">Shift</kbd> + <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">N</kbd> 新建笔记本，
            按 <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">Ctrl</kbd> + <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px]">B</kbd> 切换侧边栏
          </p>
        </div>
      </div>

      {showNotebookConfirm && (
        <>
          <div className="fixed inset-0 bg-black/20 z-50" onClick={() => { setShowNotebookConfirm(false); setPendingNotebookPrompt(null) }} />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[380px] max-w-[90vw]">
            <LiquidGlassCard className="p-5" displacementScale={8}>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-400/20 to-orange-400/20 flex items-center justify-center text-amber-600">
                  <BookOpen size={20} />
                </div>
                <div>
                  <h3 className="text-base font-semibold">切换到笔记本模式</h3>
                  <p className="text-xs text-gray-500">笔记本支持分章节整理学习笔记</p>
                </div>
              </div>
              <p className="text-sm text-gray-600 mb-5">
                {pendingNotebookPrompt
                  ? '将创建新笔记本并开始本次学习记录。笔记本内的对话会自动整理成分章节的学习笔记。'
                  : '确定要创建新笔记本吗？'}
              </p>
              <div className="flex justify-end gap-2">
                <button
                  className="px-4 py-2 text-sm rounded-lg hover:bg-gray-100 transition-colors"
                  onClick={() => { setShowNotebookConfirm(false); setPendingNotebookPrompt(null) }}
                >
                  取消
                </button>
                <button
                  className="px-4 py-2 text-sm rounded-lg bg-[#3370ff] text-white hover:bg-[#2860e6] transition-colors"
                  onClick={confirmCreateNotebook}
                >
                  创建笔记本
                </button>
              </div>
            </LiquidGlassCard>
          </div>
        </>
      )}
    </>
  )
}
