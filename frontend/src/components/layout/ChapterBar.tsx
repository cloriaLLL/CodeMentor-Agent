import { useState, useEffect } from 'react'
import { Plus, MoreVertical, Pencil, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LiquidGlassCard } from '@/components/ui/liquid-glass-card'
import { useChat } from '@/contexts/ChatContext'
import { cn } from '@/lib/utils'

export function ChapterBar() {
  const { getCurrentChat, getCurrentChapters, dispatch } = useChat()
  const currentChat = getCurrentChat()
  const chapters = getCurrentChapters()
  const [contextMenu, setContextMenu] = useState<{
    id: string
    x: number
    y: number
  } | null>(null)
  const [renameDialog, setRenameDialog] = useState<{
    id: string
    title: string
  } | null>(null)

  const isNotebook = currentChat?.type === 'notebook' && chapters.length > 0

  useEffect(() => {
    const handleClickOutside = () => setContextMenu(null)
    if (contextMenu) {
      document.addEventListener('click', handleClickOutside)
      return () => document.removeEventListener('click', handleClickOutside)
    }
  }, [contextMenu])

  if (!isNotebook) return null

  const activeChapterId = currentChat?.activeChapterId

  const handleAddChapter = () => {
    if (!currentChat) return
    const chapterNum = chapters.length + 1
    dispatch({
      type: 'ADD_CHAPTER',
      payload: {
        notebookId: currentChat.id,
        title: `第${chapterNum}章`,
      },
    })
  }

  const handleSelectChapter = (chapterId: string) => {
    if (!currentChat) return
    dispatch({
      type: 'SELECT_CHAPTER',
      payload: { notebookId: currentChat.id, chapterId },
    })
  }

  const handleDeleteChapter = (chapterId: string) => {
    if (!currentChat) return
    if (chapters.length <= 1) {
      alert('笔记本至少需要保留一个章节')
      return
    }
    dispatch({
      type: 'DELETE_CHAPTER',
      payload: { notebookId: currentChat.id, chapterId },
    })
    setContextMenu(null)
  }

  const handleRename = () => {
    if (!contextMenu) return
    const chapter = chapters.find(ch => ch.id === contextMenu.id)
    if (chapter) {
      setRenameDialog({ id: chapter.id, title: chapter.title })
    }
    setContextMenu(null)
  }

  const confirmRename = () => {
    if (!renameDialog || !currentChat) return
    dispatch({
      type: 'RENAME_CHAPTER',
      payload: {
        notebookId: currentChat.id,
        chapterId: renameDialog.id,
        title: renameDialog.title,
      },
    })
    setRenameDialog(null)
  }

  return (
    <>
      <div className="flex-shrink-0 px-4 pb-3 overflow-x-auto">
        <div className="max-w-3xl mx-auto flex items-center gap-2">
          {chapters.map(chapter => (
            <div key={chapter.id} className="relative group flex-shrink-0">
              <button
                className={cn(
                  'px-3 py-1.5 pr-7 text-xs rounded-full transition-all flex items-center gap-1',
                  activeChapterId === chapter.id
                    ? 'bg-gradient-to-br from-[#3370ff] to-[#5e8bff] text-white shadow-md shadow-blue-500/20'
                    : 'liquid-glass-base text-gray-600 hover:text-[#3370ff]'
                )}
                onClick={() => handleSelectChapter(chapter.id)}
                onContextMenu={e => {
                  e.preventDefault()
                  e.stopPropagation()
                  setContextMenu({ id: chapter.id, x: e.clientX, y: e.clientY })
                }}
              >
                {chapter.title}
              </button>
              <button
                className={cn(
                  'absolute right-1 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full flex items-center justify-center transition-all opacity-0 group-hover:opacity-100',
                  activeChapterId === chapter.id
                    ? 'bg-white/20 text-white hover:bg-red-500'
                    : 'bg-black/10 text-gray-500 hover:bg-red-500 hover:text-white'
                )}
                onClick={e => {
                  e.stopPropagation()
                  setContextMenu({
                    id: chapter.id,
                    x: e.clientX,
                    y: e.clientY,
                  })
                }}
              >
                <MoreVertical size={10} />
              </button>
            </div>
          ))}
          <button
            className="px-3 py-1.5 text-xs rounded-full border border-dashed border-gray-300 text-gray-400 hover:border-blue-400 hover:text-blue-500 transition-all flex items-center gap-1 flex-shrink-0"
            onClick={handleAddChapter}
          >
            <Plus size={12} />
            新章节
          </button>
        </div>
      </div>

      {contextMenu && (
        <>
          <LiquidGlassCard
            className="fixed z-50 py-1 min-w-[140px]"
            style={{ left: contextMenu.x, top: contextMenu.y }}
            displacementScale={8}
          >
            <button
              className="w-full px-3 py-2 flex items-center gap-2 text-sm text-left hover:bg-black/5 transition-colors"
              onClick={handleRename}
            >
              <Pencil size={13} />
              重命名
            </button>
            <button
              className="w-full px-3 py-2 flex items-center gap-2 text-sm text-left text-red-500 hover:bg-red-50 transition-colors"
              onClick={() => handleDeleteChapter(contextMenu.id)}
            >
              <Trash2 size={13} />
              删除章节
            </button>
          </LiquidGlassCard>
        </>
      )}

      {renameDialog && (
        <>
          <div
            className="fixed inset-0 bg-black/20 z-50"
            onClick={() => setRenameDialog(null)}
          />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[320px] max-w-[90vw]">
            <LiquidGlassCard className="p-5" displacementScale={8}>
              <h3 className="text-sm font-semibold mb-3">重命名章节</h3>
              <input
                type="text"
                value={renameDialog.title}
                onChange={e =>
                  setRenameDialog({ ...renameDialog, title: e.target.value })
                }
                className="w-full h-9 px-3 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500/30 mb-4 bg-white/80"
                autoFocus
                onKeyDown={e => {
                  if (e.key === 'Enter') confirmRename()
                  if (e.key === 'Escape') setRenameDialog(null)
                }}
              />
              <div className="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setRenameDialog(null)}
                >
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
    </>
  )
}
