import React, { createContext, useContext, useReducer, useEffect, useCallback, useRef } from 'react'
import type { Chat, Message, Chapter, Model } from '@/types'
import { generateId } from '@/lib/utils'

interface ChatState {
  chats: Chat[]
  notebooks: Chat[]
  currentChatId: string | null
  currentView: 'chats' | 'notebooks'
  sidebarOpen: boolean
  modelList: Model[]
  currentModel: string
  isGenerating: boolean
  abortController: AbortController | null
}

type ChatAction =
  | { type: 'SET_CHATS'; payload: { chats: Chat[]; notebooks: Chat[] } }
  | { type: 'SET_MODEL_LIST'; payload: Model[] }
  | { type: 'SET_CURRENT_MODEL'; payload: string }
  | { type: 'SET_VIEW'; payload: 'chats' | 'notebooks' }
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'SET_SIDEBAR'; payload: boolean }
  | { type: 'NEW_CHAT'; payload: 'chat' | 'notebook'; id?: string }
  | { type: 'SELECT_CHAT'; payload: string }
  | { type: 'DELETE_CHAT'; payload: string }
  | { type: 'RENAME_CHAT'; payload: { id: string; title: string } }
  | { type: 'ADD_MESSAGE'; payload: { chatId: string; message: Message } }
  | { type: 'UPDATE_MESSAGE'; payload: { chatId: string; messageId: string; content: string } }
  | { type: 'FINISH_MESSAGE'; payload: { chatId: string; messageId: string } }
  | { type: 'SET_GENERATING'; payload: boolean }
  | { type: 'SET_ABORT_CONTROLLER'; payload: AbortController | null }
  | { type: 'ADD_CHAPTER'; payload: { notebookId: string; title: string } }
  | { type: 'DELETE_CHAPTER'; payload: { notebookId: string; chapterId: string } }
  | { type: 'RENAME_CHAPTER'; payload: { notebookId: string; chapterId: string; title: string } }
  | { type: 'SELECT_CHAPTER'; payload: { notebookId: string; chapterId: string } }
  | { type: 'AUTO_TITLE'; payload: { chatId: string; title: string } }

const initialState: ChatState = {
  chats: [],
  notebooks: [],
  currentChatId: null,
  currentView: 'chats',
  sidebarOpen: true,
  modelList: [],
  currentModel: '',
  isGenerating: false,
  abortController: null,
}

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'SET_CHATS': {
      const { chats, notebooks } = action.payload
      return { ...state, chats, notebooks }
    }
    case 'SET_MODEL_LIST':
      return { ...state, modelList: action.payload }
    case 'SET_CURRENT_MODEL':
      return { ...state, currentModel: action.payload }
    case 'SET_VIEW':
      return { ...state, currentView: action.payload }
    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarOpen: !state.sidebarOpen }
    case 'SET_SIDEBAR':
      return { ...state, sidebarOpen: action.payload }
    case 'NEW_CHAT': {
      const now = new Date().toISOString()
      const newChat: Chat = {
        id: action.id ?? generateId(),
        title: action.payload === 'chat' ? '新对话' : '新笔记本',
        type: action.payload,
        messages: [],
        conversationId: generateId(),
        chapters: action.payload === 'notebook'
          ? [{ id: generateId(), title: '第1章', messages: [], conversationId: generateId(), createdAt: now, updatedAt: now }]
          : undefined,
        activeChapterId: action.payload === 'notebook' ? undefined : undefined,
        createdAt: now,
        updatedAt: now,
      }
      if (action.payload === 'notebook' && newChat.chapters && newChat.chapters[0]) {
        newChat.activeChapterId = newChat.chapters[0].id
      }
      return {
        ...state,
        [action.payload === 'chat' ? 'chats' : 'notebooks']: [
          newChat,
          ...(action.payload === 'chat' ? state.chats : state.notebooks),
        ],
        currentChatId: newChat.id,
        currentView: action.payload === 'chat' ? 'chats' : 'notebooks',
      }
    }
    case 'SELECT_CHAT':
      return { ...state, currentChatId: action.payload }
    case 'DELETE_CHAT': {
      const isChat = state.chats.some(c => c.id === action.payload)
      const list = isChat ? state.chats : state.notebooks
      const newList = list.filter(c => c.id !== action.payload)
      const newCurrentId = state.currentChatId === action.payload
        ? newList[0]?.id ?? null
        : state.currentChatId
      return {
        ...state,
        [isChat ? 'chats' : 'notebooks']: newList,
        currentChatId: newCurrentId,
      }
    }
    case 'RENAME_CHAT': {
      const updateList = (list: Chat[]) =>
        list.map(c =>
          c.id === action.payload.id ? { ...c, title: action.payload.title, updatedAt: new Date().toISOString() } : c
        )
      return {
        ...state,
        chats: updateList(state.chats),
        notebooks: updateList(state.notebooks),
      }
    }
    case 'ADD_MESSAGE': {
      const addToMessages = (chat: Chat): Chat => {
        if (chat.type === 'notebook' && chat.chapters && chat.activeChapterId) {
          return {
            ...chat,
            chapters: chat.chapters.map(ch =>
              ch.id === chat.activeChapterId
                ? { ...ch, messages: [...ch.messages, action.payload.message], updatedAt: new Date().toISOString() }
                : ch
            ),
            updatedAt: new Date().toISOString(),
          }
        }
        return { ...chat, messages: [...chat.messages, action.payload.message], updatedAt: new Date().toISOString() }
      }
      return {
        ...state,
        chats: state.chats.map(c => (c.id === action.payload.chatId ? addToMessages(c) : c)),
        notebooks: state.notebooks.map(c => (c.id === action.payload.chatId ? addToMessages(c) : c)),
      }
    }
    case 'UPDATE_MESSAGE': {
      const updateInMessages = (chat: Chat): Chat => {
        if (chat.type === 'notebook' && chat.chapters && chat.activeChapterId) {
          return {
            ...chat,
            chapters: chat.chapters.map(ch =>
              ch.id === chat.activeChapterId
                ? {
                    ...ch,
                    messages: ch.messages.map(m =>
                      m.id === action.payload.messageId ? { ...m, content: action.payload.content } : m
                    ),
                  }
                : ch
            ),
          }
        }
        return {
          ...chat,
          messages: chat.messages.map(m =>
            m.id === action.payload.messageId ? { ...m, content: action.payload.content } : m
          ),
        }
      }
      return {
        ...state,
        chats: state.chats.map(c => (c.id === action.payload.chatId ? updateInMessages(c) : c)),
        notebooks: state.notebooks.map(c => (c.id === action.payload.chatId ? updateInMessages(c) : c)),
      }
    }
    case 'FINISH_MESSAGE': {
      const finishInMessages = (chat: Chat): Chat => {
        if (chat.type === 'notebook' && chat.chapters && chat.activeChapterId) {
          return {
            ...chat,
            chapters: chat.chapters.map(ch =>
              ch.id === chat.activeChapterId
                ? {
                    ...ch,
                    messages: ch.messages.map(m =>
                      m.id === action.payload.messageId ? { ...m, generating: false } : m
                    ),
                  }
                : ch
            ),
          }
        }
        return {
          ...chat,
          messages: chat.messages.map(m =>
            m.id === action.payload.messageId ? { ...m, generating: false } : m
          ),
        }
      }
      return {
        ...state,
        chats: state.chats.map(c => (c.id === action.payload.chatId ? finishInMessages(c) : c)),
        notebooks: state.notebooks.map(c => (c.id === action.payload.chatId ? finishInMessages(c) : c)),
      }
    }
    case 'SET_GENERATING':
      return { ...state, isGenerating: action.payload }
    case 'SET_ABORT_CONTROLLER':
      return { ...state, abortController: action.payload }
    case 'ADD_CHAPTER': {
      const now = new Date().toISOString()
      const newChapter: Chapter = {
        id: generateId(),
        title: action.payload.title,
        messages: [],
        conversationId: generateId(),
        createdAt: now,
        updatedAt: now,
      }
      return {
        ...state,
        notebooks: state.notebooks.map(nb =>
          nb.id === action.payload.notebookId && nb.chapters
            ? { ...nb, chapters: [...nb.chapters, newChapter], activeChapterId: newChapter.id, updatedAt: now }
            : nb
        ),
      }
    }
    case 'DELETE_CHAPTER': {
      return {
        ...state,
        notebooks: state.notebooks.map(nb => {
          if (nb.id !== action.payload.notebookId || !nb.chapters) return nb
          const remaining = nb.chapters.filter(ch => ch.id !== action.payload.chapterId)
          if (remaining.length === 0) return nb
          return {
            ...nb,
            chapters: remaining,
            activeChapterId:
              nb.activeChapterId === action.payload.chapterId
                ? remaining[0].id
                : nb.activeChapterId,
            updatedAt: new Date().toISOString(),
          }
        }),
      }
    }
    case 'RENAME_CHAPTER': {
      return {
        ...state,
        notebooks: state.notebooks.map(nb =>
          nb.id === action.payload.notebookId && nb.chapters
            ? {
                ...nb,
                chapters: nb.chapters.map(ch =>
                  ch.id === action.payload.chapterId
                    ? { ...ch, title: action.payload.title, updatedAt: new Date().toISOString() }
                    : ch
                ),
              }
            : nb
        ),
      }
    }
    case 'SELECT_CHAPTER': {
      return {
        ...state,
        notebooks: state.notebooks.map(nb =>
          nb.id === action.payload.notebookId
            ? { ...nb, activeChapterId: action.payload.chapterId }
            : nb
        ),
      }
    }
    case 'AUTO_TITLE': {
      const applyTitle = (list: Chat[]): Chat[] =>
        list.map(c =>
          c.id === action.payload.chatId
            ? { ...c, title: action.payload.title, updatedAt: new Date().toISOString() }
            : c
        )
      return {
        ...state,
        chats: applyTitle(state.chats),
        notebooks: applyTitle(state.notebooks),
      }
    }
    default:
      return state
  }
}

interface ChatContextType extends ChatState {
  dispatch: React.Dispatch<ChatAction>
  getCurrentChat: () => Chat | null
  getCurrentMessages: () => Message[]
  getCurrentChapters: () => Chapter[]
  sendMessage: (content: string) => Promise<void>
  stopGeneration: () => void
  loadFromStorage: () => void
  saveToStorage: (chats: Chat[], notebooks: Chat[], currentChatId: string | null, currentView: 'chats' | 'notebooks') => void
}

const ChatContext = createContext<ChatContextType | null>(null)

const STORAGE_KEY = 'codementor_data'

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState)

  const getCurrentChat = useCallback((): Chat | null => {
    if (!state.currentChatId) return null
    return [...state.chats, ...state.notebooks].find(c => c.id === state.currentChatId) ?? null
  }, [state.chats, state.notebooks, state.currentChatId])

  const getCurrentMessages = useCallback((): Message[] => {
    const chat = getCurrentChat()
    if (!chat) return []
    if (chat.type === 'notebook' && chat.chapters && chat.activeChapterId) {
      const chapter = chat.chapters.find(ch => ch.id === chat.activeChapterId)
      return chapter?.messages ?? []
    }
    return chat.messages
  }, [getCurrentChat])

  const getCurrentChapters = useCallback((): Chapter[] => {
    const chat = getCurrentChat()
    if (!chat || chat.type !== 'notebook' || !chat.chapters) return []
    return chat.chapters
  }, [getCurrentChat])

  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const saveToStorage = useCallback((chats: Chat[], notebooks: Chat[], currentChatId: string | null, currentView: 'chats' | 'notebooks') => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => {
      try {
        const data = { chats, notebooks, currentChatId, currentView }
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
      } catch (e) {
        console.error('[Storage] Save failed:', e)
      }
    }, 500)
  }, [])

  const loadFromStorage = useCallback(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const data = JSON.parse(saved)
        // Clean generating flags from all messages (crash recovery)
        const cleanMessages = (msgs: Message[]): Message[] =>
          msgs.map(m => m.generating ? { ...m, generating: false } : m)
        const cleanChats = (chats: Chat[]): Chat[] =>
          chats.map(c => ({
            ...c,
            conversationId: c.conversationId || generateId(),
            messages: cleanMessages(c.messages),
            chapters: c.chapters?.map(ch => ({
              ...ch,
              conversationId: ch.conversationId || generateId(),
              messages: cleanMessages(ch.messages),
            })),
          }))
        const chats = cleanChats(data.chats ?? [])
        const notebooks = cleanChats(data.notebooks ?? [])
        const allChats = [...chats, ...notebooks]

        dispatch({ type: 'SET_CHATS', payload: { chats, notebooks } })

        const savedChatId = data.currentChatId
        if (savedChatId && allChats.find(c => c.id === savedChatId)) {
          dispatch({ type: 'SELECT_CHAT', payload: savedChatId })
          dispatch({ type: 'SET_VIEW', payload: data.currentView || 'chats' })
        } else if (allChats.length > 0) {
          const latest = allChats.sort((a, b) =>
            new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
          )[0]
          dispatch({ type: 'SELECT_CHAT', payload: latest.id })
          dispatch({ type: 'SET_VIEW', payload: latest.type === 'notebook' ? 'notebooks' : 'chats' })
        } else {
          dispatch({ type: 'NEW_CHAT', payload: 'chat' })
        }
      } else {
        dispatch({ type: 'NEW_CHAT', payload: 'chat' })
      }
    } catch (e) {
      console.error('Failed to load from storage:', e)
      dispatch({ type: 'NEW_CHAT', payload: 'chat' })
    }
  }, [])

  useEffect(() => {
    loadFromStorage()
    fetch('/api/llm_status')
      .then(res => res.json())
      .then(data => {
        const models = (data.available_zhipu_models || {})
        const seen = new Set<string>()
        const modelList = Object.keys(models)
          .filter(id => {
            if (seen.has(id)) return false
            seen.add(id)
            return true
          })
          .map(id => ({
            id,
            name: models[id]?.name || id,
          }))
        if (modelList.length > 0) {
          dispatch({ type: 'SET_MODEL_LIST', payload: modelList })
          dispatch({ type: 'SET_CURRENT_MODEL', payload: data.current_model || modelList[0].id })
        } else {
          dispatch({
            type: 'SET_MODEL_LIST',
            payload: [{ id: data.provider || 'mock', name: data.is_mock ? 'Mock 模式' : `${data.provider} 模型` }],
          })
          dispatch({ type: 'SET_CURRENT_MODEL', payload: data.provider || 'mock' })
        }
      })
      .catch(() => {
        dispatch({
          type: 'SET_MODEL_LIST',
          payload: [{ id: 'mock', name: '离线模式' }],
        })
        dispatch({ type: 'SET_CURRENT_MODEL', payload: 'mock' })
      })
  }, [loadFromStorage])

  useEffect(() => {
    saveToStorage(state.chats, state.notebooks, state.currentChatId, state.currentView)
  }, [state.chats, state.notebooks, state.currentChatId, state.currentView, saveToStorage])

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 768) {
        dispatch({ type: 'SET_SIDEBAR', payload: false })
      }
    }
    window.addEventListener('resize', handleResize)
    handleResize()
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'n' && !e.shiftKey && !e.altKey) {
        const target = e.target as HTMLElement
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return
        e.preventDefault()
        dispatch({ type: 'NEW_CHAT', payload: 'chat' })
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'b' && !e.shiftKey && !e.altKey) {
        const target = e.target as HTMLElement
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return
        e.preventDefault()
        dispatch({ type: 'TOGGLE_SIDEBAR' })
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'N') {
        const target = e.target as HTMLElement
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return
        e.preventDefault()
        dispatch({ type: 'NEW_CHAT', payload: 'notebook' })
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const generateAutoTitle = useCallback((userMessage: string, cid: string) => {
    const extractTitle = (text: string): string => {
      const t = text.trim().replace(/[\r\n]+/g, ' ')
      let title = t.slice(0, 30)
      const codeMatch = t.match(/```[\s\S]*?```/)
      if (codeMatch && codeMatch.index === 0) {
        title = t.replace(/```[\s\S]*?```/, '').trim().slice(0, 30)
      }
      const urlPattern = /https?:\/\/[^\s]+/g
      title = title.replace(urlPattern, '链接')

      const stopWords = ['请', '帮我', '帮我写', '帮我写一个', '帮我实现', '如何', '怎么', '什么是', '请问', '你好', '我想', '我想要', '能不能', '可以', '写一个', '实现一个', '教我', '告诉我', '解释一下']
      for (const w of stopWords) {
        if (title.startsWith(w) && title.length > w.length + 2) {
          title = title.slice(w.length).trim()
          break
        }
      }

      if (!title) title = t.slice(0, 20)
      if (t.length > 30) title += '…'
      return title || '新对话'
    }

    const localTitle = extractTitle(userMessage)

    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: `请为以下用户提问生成一个不超过15个字的简短对话标题，直接输出标题文字，不要任何解释或标点：\n\n${userMessage.slice(0, 200)}`,
        history: [],
      }),
    })
      .then(res => res.json())
      .then(data => {
        if (data.response) {
          let llmTitle = data.response.trim()
          llmTitle = llmTitle.replace(/^[「"「『\s]+|[」"』\s]+$/g, '')
          llmTitle = llmTitle.replace(/标题[：:]\s*/, '')
          if (llmTitle.length > 0 && llmTitle.length <= 30) {
            dispatch({ type: 'AUTO_TITLE', payload: { chatId: cid, title: llmTitle } })
            return
          }
        }
        dispatch({ type: 'AUTO_TITLE', payload: { chatId: cid, title: localTitle } })
      })
      .catch(() => {
        dispatch({ type: 'AUTO_TITLE', payload: { chatId: cid, title: localTitle } })
      })
  }, [dispatch])

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || state.isGenerating) return

      let chatId = state.currentChatId
      const chat = getCurrentChat()
      if (!chat) {
        chatId = generateId()
        dispatch({ type: 'NEW_CHAT', payload: 'chat', id: chatId })
      }

      const isNewChat = !chat || (chat.messages.length === 0 && !(chat.chapters?.some(ch => ch.messages.length > 0)))
      const defaultTitle = chat?.type === 'notebook' ? '新笔记本' : '新对话'
      const needsAutoTitle = isNewChat || chat?.title === defaultTitle

      const userMsg: Message = {
        id: generateId(),
        role: 'user',
        content: content.trim(),
        timestamp: new Date().toISOString(),
      }
      dispatch({ type: 'ADD_MESSAGE', payload: { chatId: chatId!, message: userMsg } })

      const aiMsg: Message = {
        id: generateId(),
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        generating: true,
      }
      dispatch({ type: 'ADD_MESSAGE', payload: { chatId: chatId!, message: aiMsg } })
      dispatch({ type: 'SET_GENERATING', payload: true })

      const abortController = new AbortController()
      dispatch({ type: 'SET_ABORT_CONTROLLER', payload: abortController })

      const timeoutId = setTimeout(() => abortController.abort(), 45000)

      try {
        const isNotebookChat = chat?.type === 'notebook'

        // Determine conversation IDs for server-side history management
        let conversationId: string | undefined
        let parentConversationId: string | undefined

        if (isNotebookChat && chat) {
          // Notebook chapter: use chapter's conversationId, parent is notebook's conversationId
          const activeChapter = chat.chapters?.find(ch => ch.id === chat.activeChapterId)
          conversationId = activeChapter?.conversationId
          parentConversationId = chat.conversationId
        } else {
          // Regular chat
          conversationId = chat?.conversationId
        }

        // Build request body: use conversation_id when available, otherwise fall back to history
        const hasConvId = !!conversationId
        const requestBody: Record<string, unknown> = {
          message: content.trim(),
        }
        if (hasConvId) {
          // Backend will load history from ConversationStore
          requestBody.history = []
          requestBody.conversation_id = conversationId
        } else {
          // Fallback for old chats without conversationId: send full history
          const rawHistory = [...getCurrentMessages().filter(m => !m.generating), userMsg]
          requestBody.history = rawHistory.map(m => ({ role: m.role, content: m.content }))
        }
        if (isNotebookChat) {
          requestBody.mode = 'notebook'
          if (parentConversationId) {
            requestBody.parent_conversation_id = parentConversationId
          }
        }

        const response = await fetch('/api/chat_stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
          signal: abortController.signal,
        })

        if (!response.ok || !response.body) {
          throw new Error(`请求失败 (HTTP ${response.status})`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let fullContent = ''
        let buffer = ''
        let eventDataParts: string[] = []

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          let idx = 0

          while (idx < buffer.length) {
            const newlineIdx = buffer.indexOf('\n', idx)
            if (newlineIdx === -1) break

            const line = buffer.slice(idx, newlineIdx)
            idx = newlineIdx + 1

            if (line === '') {
              if (eventDataParts.length > 0) {
                const dataStr = eventDataParts.join('\n')
                try {
                  const parsed = JSON.parse(dataStr)
                  if (parsed.token) {
                    fullContent += parsed.token
                    dispatch({
                      type: 'UPDATE_MESSAGE',
                      payload: { chatId: chatId!, messageId: aiMsg.id, content: fullContent },
                    })
                  } else if (parsed.done) {
                    // Done event, ignore here, loop exits on stream done
                  } else if (parsed.error) {
                    fullContent += `\n\n**错误**：${parsed.error}`
                    dispatch({
                      type: 'UPDATE_MESSAGE',
                      payload: { chatId: chatId!, messageId: aiMsg.id, content: fullContent },
                    })
                  }
                } catch {
                  // Non-JSON data, skip silently
                }
              }
              eventDataParts = []
              continue
            }

            if (line.startsWith(':')) {
              continue
            }

            if (line.startsWith('event: ')) {
              // Event type parsed but not used yet (heartbeat/start events are handled by presence alone)
            } else if (line.startsWith('data: ')) {
              eventDataParts.push(line.slice(6))
            } else if (line.startsWith('data:')) {
              eventDataParts.push(line.slice(5))
            }
          }

          buffer = buffer.slice(idx)
        }

        if (!fullContent) {
          fullContent = `这是对「${content}」的模拟回复。后端API未连接或返回空响应。\n\n你可以：\n1. 继续提问\n2. 新建笔记本组织学习内容\n3. 切换侧边栏视图管理对话`
          dispatch({
            type: 'UPDATE_MESSAGE',
            payload: { chatId: chatId!, messageId: aiMsg.id, content: fullContent },
          })
        }
      } catch (err: unknown) {
        const isAborted = err instanceof Error && err.name === 'AbortError'
        if (!isAborted) {
          console.error('Chat error:', err)
          dispatch({
            type: 'UPDATE_MESSAGE',
            payload: {
              chatId: chatId!,
              messageId: aiMsg.id,
              content: '⚠️ 网络错误，请检查后端连接后重试。',
            },
          })
        }
      } finally {
        clearTimeout(timeoutId)
        dispatch({ type: 'FINISH_MESSAGE', payload: { chatId: chatId!, messageId: aiMsg.id } })
        dispatch({ type: 'SET_GENERATING', payload: false })
        dispatch({ type: 'SET_ABORT_CONTROLLER', payload: null })

        if (needsAutoTitle && chatId) {
          generateAutoTitle(content.trim(), chatId)
        }
      }
    },
    [state.currentChatId, state.isGenerating, state.currentModel, getCurrentChat, getCurrentMessages, generateAutoTitle]
  )

  const stopGeneration = useCallback(() => {
    if (state.abortController) {
      state.abortController.abort()
    }
  }, [state.abortController])

  const value: ChatContextType = {
    ...state,
    dispatch,
    getCurrentChat,
    getCurrentMessages,
    getCurrentChapters,
    sendMessage,
    stopGeneration,
    loadFromStorage,
    saveToStorage,
  }

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used within ChatProvider')
  return ctx
}
