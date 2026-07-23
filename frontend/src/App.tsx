import { ChatProvider } from '@/contexts/ChatContext'
import { ExerciseProvider } from '@/contexts/ExerciseContext'
import { Sidebar } from '@/components/layout/Sidebar'
import { TopBar } from '@/components/layout/TopBar'
import { ChapterBar } from '@/components/layout/ChapterBar'
import { ChatArea } from '@/components/chat/ChatArea'
import { ChatInput } from '@/components/chat/ChatInput'
import { ExercisePanel } from '@/components/exercise/ExercisePanel'
import { LiquidGlassFilters } from '@/components/ui/liquid-glass-card'

function App() {
  return (
    <ChatProvider>
      <ExerciseProvider>
        <LiquidGlassFilters />
        <div className="flex h-screen w-screen overflow-hidden">
          <Sidebar />
          <main className="flex-1 flex flex-col overflow-hidden min-w-0 relative">
            <TopBar />
            <ChapterBar />
            <ChatArea />
            <ChatInput />
          </main>
        </div>
        <ExercisePanel />
      </ExerciseProvider>
    </ChatProvider>
  )
}

export default App
