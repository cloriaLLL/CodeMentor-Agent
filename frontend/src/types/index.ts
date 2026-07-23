export type MessageRole = 'user' | 'assistant'

export interface Message {
  id: string
  role: MessageRole
  content: string
  timestamp: string
  generating?: boolean
}

export interface Chapter {
  id: string
  title: string
  messages: Message[]
  conversationId?: string
  createdAt: string
  updatedAt: string
}

export interface Chat {
  id: string
  title: string
  type: 'chat' | 'notebook'
  messages: Message[]
  chapters?: Chapter[]
  activeChapterId?: string
  conversationId?: string
  createdAt: string
  updatedAt: string
}

export interface Model {
  id: string
  name: string
}

export interface AppState {
  chats: Chat[]
  notebooks: Chat[]
  currentChatId: string | null
  currentView: 'chats' | 'notebooks'
  sidebarOpen: boolean
  modelList: Model[]
  currentModel: string
}
