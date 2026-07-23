import { useState } from 'react'
import {
  MessageSquare,
  BookOpen,
  Plus,
  Search,
  ChevronLeft,
  MoreVertical,
  Trash2,
  Pencil,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LiquidGlassCard } from '@/components/ui/liquid-glass-card'
import { useChat } from '@/contexts/ChatContext'
import type { Chat } from '@/types'
import { cn, formatTime } from '@/lib/utils'

export function Sidebar() {
  const {
    chats,
    notebooks,
    currentChatId,
    currentView,
    sidebarOpen,
    dispatch,
  } = useChat()
  const [searchQuery, setSearchQuery] = useState('')
  const [contextMenu, setContextMenu] = useState<{
    id: string
    x: number
    y: number
    type: 'chat' | 'notebook'
  } | null>(null)
  const [renameDialog, setRenameDialog] = useState<{
    id: string
    title: string
  } | null>(null)
  const [newFolderDialog, setNewFolderDialog] = useState(false)

  const currentList = currentView === 'chats' ? chats : notebooks

  const filteredList = currentList.filter(c =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleContextMenu = (
    e: React.MouseEvent,
    chat: Chat,
    type: 'chat' | 'notebook'
  ) => {
    e.preventDefault()
    e.stopPropagation()
    setContextMenu({ id: chat.id, x: e.clientX, y: e.clientY, type })
  }

  const closeContextMenu = () => setContextMenu(null)

  const handleDelete = (id: string) => {
    dispatch({ type: 'DELETE_CHAT', payload: id })
    closeContextMenu()
  }

  const handleRename = () => {
    if (!contextMenu) return
    const chat = [...chats, ...notebooks].find(c => c.id === contextMenu.id)
    if (chat) {
      setRenameDialog({ id: chat.id, title: chat.title })
    }
    closeContextMenu()
  }

  const confirmRename = () => {
    if (!renameDialog) return
    dispatch({
      type: 'RENAME_CHAT',
      payload: { id: renameDialog.id, title: renameDialog.title },
    })
    setRenameDialog(null)
  }

  return (
    <>
      <aside
        className={cn(
          'h-full flex flex-col transition-all duration-300 ease-out z-40',
          sidebarOpen ? 'w-[var(--sidebar-width)] opacity-100' : 'w-0 opacity-0 pointer-events-none overflow-hidden'
        )}
      >
        <LiquidGlassCard
          className="h-full flex flex-col rounded-none border-0 border-r border-white/60"
          displacementScale={8}
          interactive={false}
        >
          <div className="flex items-center gap-3 px-4 py-3 border-b border-black/5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#3370ff] to-[#5e8bff] flex items-center justify-center text-white font-bold text-lg shadow-md shadow-blue-500/20">
              C
            </div>
            <span className="font-semibold text-base flex-1">CodeMentor</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => dispatch({ type: 'TOGGLE_SIDEBAR' })}
            >
              <ChevronLeft size={18} />
            </Button>
          </div>

          <div className="px-3 pt-3 pb-2">
            <Button
              variant="primary"
              className="w-full h-10 text-sm"
              onClick={() =>
                dispatch({
                  type: 'NEW_CHAT',
                  payload: currentView === 'chats' ? 'chat' : 'notebook',
                })
              }
            >
              <Plus size={16} />
              {currentView === 'chats' ? '新建对话' : '新建笔记本'}
            </Button>
          </div>

          <div className="px-3 pb-2">
            <div className="relative">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
              <input
                type="text"
                placeholder="搜索..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full h-8 pl-8 pr-3 text-sm bg-black/5 border border-black/5 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500/30 transition-all placeholder:text-gray-400"
              />
            </div>
          </div>

          <div className="flex gap-1 px-3 pb-2">
            <button
              className={cn(
                'flex-1 h-8 flex items-center justify-center gap-1.5 text-xs rounded-lg font-medium transition-all',
                currentView === 'chats'
                  ? 'bg-[#3370ff]/10 text-[#3370ff]'
                  : 'text-gray-500 hover:bg-black/5'
              )}
              onClick={() => dispatch({ type: 'SET_VIEW', payload: 'chats' })}
            >
              <MessageSquare size={14} />
              对话
            </button>
            <button
              className={cn(
                'flex-1 h-8 flex items-center justify-center gap-1.5 text-xs rounded-lg font-medium transition-all',
                currentView === 'notebooks'
                  ? 'bg-[#3370ff]/10 text-[#3370ff]'
                  : 'text-gray-500 hover:bg-black/5'
              )}
              onClick={() => dispatch({ type: 'SET_VIEW', payload: 'notebooks' })}
            >
              <BookOpen size={14} />
              笔记本
            </button>
          </div>

          <div className="flex items-center justify-between px-4 py-2">
            <span className="text-xs font-medium text-gray-500">
              {currentView === 'chats' ? '最近对话' : '我的笔记本'}
            </span>
            {currentView === 'notebooks' && (
              <button
                className="h-6 w-6 rounded flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-black/5 transition-colors"
                onClick={() => setNewFolderDialog(true)}
                title="新建分组"
              >
                <Plus size={14} />
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto px-2 pb-2" onClick={closeContextMenu}>
            {filteredList.length === 0 ? (
              <div className="text-center py-12 text-gray-400 text-sm">
                {currentView === 'chats' ? '暂无对话' : '暂无笔记本'}
              </div>
            ) : (
              filteredList.map(item => (
                <div
                  key={item.id}
                  className={cn(
                    'group relative flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-all mb-0.5',
                    currentChatId === item.id
                      ? 'bg-[#3370ff]/10 text-[#3370ff]'
                      : 'hover:bg-black/5 text-gray-700'
                  )}
                  onClick={() => dispatch({ type: 'SELECT_CHAT', payload: item.id })}
                  onContextMenu={e =>
                    handleContextMenu(e, item, item.type)
                  }
                >
                  {item.type === 'chat' ? (
                    <MessageSquare size={15} className="flex-shrink-0 opacity-70" />
                  ) : (
                    <BookOpen size={15} className="flex-shrink-0 opacity-70" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{item.title}</div>
                    <div className="text-xs text-gray-400 truncate">
                      {formatTime(item.updatedAt)}
                      {item.type === 'notebook' && item.chapters
                        ? ` · ${item.chapters.length}个章节`
                        : ''}
                    </div>
                  </div>
                  <button
                    className="opacity-0 group-hover:opacity-100 h-6 w-6 rounded flex items-center justify-center hover:bg-black/10 transition-all"
                    onClick={e => {
                      e.stopPropagation()
                      handleContextMenu(e, item, item.type)
                    }}
                  >
                    <MoreVertical size={14} />
                  </button>
                </div>
              ))
            )}
          </div>
        </LiquidGlassCard>
      </aside>

      {contextMenu && (
        <>
          <div className="fixed inset-0 z-50" onClick={closeContextMenu} />
          <LiquidGlassCard
            className="fixed z-50 py-1 min-w-[160px]"
            style={{ left: contextMenu.x, top: contextMenu.y }}
            displacementScale={8}
          >
            <button
              className="w-full px-3 py-2 flex items-center gap-2 text-sm text-left hover:bg-black/5 transition-colors"
              onClick={handleRename}
            >
              <Pencil size={14} />
              重命名
            </button>
            <button
              className="w-full px-3 py-2 flex items-center gap-2 text-sm text-left text-red-500 hover:bg-red-50 transition-colors"
              onClick={() => handleDelete(contextMenu.id)}
            >
              <Trash2 size={14} />
              删除
            </button>
          </LiquidGlassCard>
        </>
      )}

      {renameDialog && (
        <>
          <div className="fixed inset-0 bg-black/20 z-50" onClick={() => setRenameDialog(null)} />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[360px] max-w-[90vw]">
            <LiquidGlassCard className="p-5" displacementScale={8}>
              <h3 className="text-base font-semibold mb-4">重命名</h3>
              <input
                type="text"
                value={renameDialog.title}
                onChange={e =>
                  setRenameDialog({ ...renameDialog, title: e.target.value })
                }
                className="w-full h-10 px-3 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500/30 mb-4 bg-white/80"
                autoFocus
                onKeyDown={e => {
                  if (e.key === 'Enter') confirmRename()
                  if (e.key === 'Escape') setRenameDialog(null)
                }}
              />
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => setRenameDialog(null)}>
                  取消
                </Button>
                <Button variant="primary" size="sm" onClick={confirmRename}>
                  确定
                </Button>
              </div>
            </LiquidGlassCard>
          </div>
        </>
      )}

      {newFolderDialog && (
        <>
          <div
            className="fixed inset-0 bg-black/20 z-50"
            onClick={() => setNewFolderDialog(false)}
          />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[360px] max-w-[90vw]">
            <LiquidGlassCard className="p-5" displacementScale={8}>
              <h3 className="text-base font-semibold mb-4">新建笔记本</h3>
              <input
                type="text"
                placeholder="笔记本名称"
                className="w-full h-10 px-3 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500/30 mb-4 bg-white/80"
                autoFocus
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    dispatch({ type: 'NEW_CHAT', payload: 'notebook' })
                    setNewFolderDialog(false)
                  }
                  if (e.key === 'Escape') setNewFolderDialog(false)
                }}
              />
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => setNewFolderDialog(false)}>
                  取消
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    dispatch({ type: 'NEW_CHAT', payload: 'notebook' })
                    setNewFolderDialog(false)
                  }}
                >
                  创建
                </Button>
              </div>
            </LiquidGlassCard>
          </div>
        </>
      )}
    </>
  )
}
