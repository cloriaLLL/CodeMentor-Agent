import { useEffect } from 'react'
import {
  X,
  Lightbulb,
  Loader2,
  Clock,
  Tag,
  AlertCircle,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Button } from '@/components/ui/button'
import { LiquidGlassCard } from '@/components/ui/liquid-glass-card'
import { ChoiceQuestion } from './ChoiceQuestion'
import { CodeQuestion } from './CodeQuestion'
import { ResultFeedback } from './ResultFeedback'
import { useExercise } from '@/contexts/ExerciseContext'
import { cn } from '@/lib/utils'

const TYPE_LABELS: Record<string, string> = {
  understanding: '理解型',
  modification: '修改型',
  creation: '创作型',
  project: '综合项目',
}

const TYPE_COLORS: Record<string, string> = {
  understanding: 'from-blue-500/10 to-indigo-500/5 text-blue-600 border-blue-200/50',
  modification: 'from-amber-500/10 to-orange-500/5 text-amber-600 border-amber-200/50',
  creation: 'from-purple-500/10 to-pink-500/5 text-purple-600 border-purple-200/50',
  project: 'from-emerald-500/10 to-teal-500/5 text-emerald-600 border-emerald-200/50',
}

export function ExercisePanel() {
  const {
    panelOpen,
    closePanel,
    exercise,
    result,
    isLoading,
    isSubmitting,
    isFetchingHint,
    hint,
    error,
    fetchHint,
    clearHint,
    clearError,
    reset,
    generateNext,
    lastGenerateParams,
  } = useExercise()

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && panelOpen) closePanel()
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [panelOpen, closePanel])

  if (!panelOpen) return null

  const isCodeType = exercise && ['modification', 'creation', 'project'].includes(exercise.exercise_type)

  const handleClose = () => {
    closePanel()
    setTimeout(() => reset(), 300)
  }

  return (
    <>
      <div
        className="fixed inset-0 bg-black/15 z-30 backdrop-blur-[2px] lg:hidden"
        onClick={handleClose}
        style={{ animation: 'fadeIn 0.2s ease forwards' }}
      />

      <aside
        className={cn(
          'fixed right-0 top-0 bottom-0 z-40 flex flex-col',
          'bg-white/75 backdrop-blur-2xl saturate-[200%] border-l border-white/80',
          'shadow-[0_0_60px_rgba(0,0,0,0.08)]',
          'w-full sm:w-[440px] lg:w-[480px]',
          'max-w-full'
        )}
        style={{
          animation: 'slideInRight 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards',
        }}
      >
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-black/5 flex-shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#3370ff] to-[#5e8bff] flex items-center justify-center text-white shadow-md shadow-blue-500/20 flex-shrink-0">
              <Sparkles size={15} />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-semibold text-gray-800">练习面板</div>
              <div className="text-[10px] text-gray-400">交互式题目作答</div>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-black/5 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {error && (
            <div className="mb-4 p-3 rounded-xl bg-red-50/80 border border-red-200/50 flex items-start gap-2">
              <AlertCircle size={16} className="text-red-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1 text-xs text-red-600">{error}</div>
              <button onClick={clearError} className="text-red-400 hover:text-red-600">
                <X size={14} />
              </button>
            </div>
          )}

          {isLoading && (
            <div className="flex flex-col items-center justify-center py-20 text-gray-400">
              <Loader2 size={32} className="animate-spin text-[#3370ff] mb-3" />
              <div className="text-sm">正在生成题目...</div>
              <div className="text-xs mt-1 text-gray-400">AI 正在为你量身定制练习</div>
            </div>
          )}

          {!isLoading && !exercise && (
            <div className="flex flex-col items-center justify-center py-20 text-gray-400">
              <div className="w-16 h-16 rounded-2xl bg-gray-100/80 flex items-center justify-center mb-3">
                <Sparkles size={28} className="text-gray-300" />
              </div>
              <div className="text-sm font-medium text-gray-500">暂无题目</div>
              <div className="text-xs mt-1 text-gray-400 max-w-[240px] text-center">
                在对话中点击练习按钮，或请求生成一道题目开始练习
              </div>
            </div>
          )}

          {exercise && !isLoading && (
            <div className="space-y-4">
              <div className={cn(
                'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border bg-gradient-to-br',
                TYPE_COLORS[exercise.exercise_type] || TYPE_COLORS.understanding
              )}>
                <Tag size={11} />
                {TYPE_LABELS[exercise.exercise_type] || exercise.exercise_type}
                {exercise.subtype && exercise.exercise_type === 'understanding' && (
                  <span className="opacity-70">· {exercise.subtype}</span>
                )}
              </div>

              <LiquidGlassCard className="p-4 rounded-2xl" displacementScale={6}>
                <div className="flex items-start gap-2 mb-2">
                  <div className="text-sm text-gray-800 leading-relaxed flex-1 prose prose-sm max-w-none [&_p]:my-1.5 [&_h1]:text-base [&_h1]:font-bold [&_h2]:text-sm [&_h2]:font-semibold [&_h3]:text-sm [&_h3]:font-semibold [&_ul]:my-1.5 [&_ol]:my-1.5 [&_li]:my-0.5 [&_code]:px-1 [&_code]:py-0.5 [&_code]:bg-blue-50 [&_code]:text-[#2860e1] [&_code]:rounded [&_code]:text-[0.9em] [&_code]:font-mono [&_code]:font-medium [&_strong]:text-gray-900 [&_strong]:font-semibold [&_blockquote]:my-2 [&_blockquote]:pl-3 [&_blockquote]:border-l-2 [&_blockquote]:border-blue-200 [&_blockquote]:text-gray-600 [&_blockquote]:text-xs">
                    <ReactMarkdown>{exercise.question}</ReactMarkdown>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-[11px] text-gray-400">
                  <span className="flex items-center gap-1">
                    <Clock size={10} />
                    {exercise.estimated_time_min}分钟
                  </span>
                  <span className="flex items-center gap-1">
                    <Tag size={10} />
                    {exercise.difficulty}
                  </span>
                  {exercise.knowledge_points.length > 0 && (
                    <span className="truncate">
                      {exercise.knowledge_points.slice(0, 2).join(', ')}
                    </span>
                  )}
                </div>
              </LiquidGlassCard>

              {result && (
                <ResultFeedback
                  result={result}
                  referenceSolution={exercise.reference_solution}
                  exerciseType={exercise.exercise_type}
                />
              )}

              {isCodeType ? (
                <CodeQuestion exercise={exercise} />
              ) : (
                <ChoiceQuestion exercise={exercise} />
              )}

              <div className="pt-2 border-t border-black/5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-gray-500 flex items-center gap-1.5">
                    <Lightbulb size={12} />
                    需要提示？
                  </span>
                  {hint && (
                    <button
                      onClick={clearHint}
                      className="text-[11px] text-gray-400 hover:text-[#3370ff]"
                    >
                      收起
                    </button>
                  )}
                </div>

                {!hint ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full h-8 text-xs"
                    onClick={fetchHint}
                    disabled={isFetchingHint}
                  >
                    {isFetchingHint ? (
                      <>
                        <Loader2 size={12} className="animate-spin" />
                        生成中...
                      </>
                    ) : (
                      <>
                        <Lightbulb size={12} />
                        获取提示
                      </>
                    )}
                  </Button>
                ) : (
                  <LiquidGlassCard className="p-3 rounded-xl bg-amber-50/60 border-amber-200/40" displacementScale={4}>
                    <div className="flex items-start gap-2">
                      <Lightbulb size={14} className="text-amber-500 flex-shrink-0 mt-0.5" />
                      <div className="text-xs text-amber-800 leading-relaxed whitespace-pre-wrap">
                        {hint}
                      </div>
                    </div>
                  </LiquidGlassCard>
                )}
              </div>

              {result && (
                <div className="pt-2 space-y-2">
                  {lastGenerateParams && (
                    <Button
                      variant="primary"
                      size="sm"
                      className="w-full h-9 text-xs"
                      onClick={generateNext}
                      disabled={isLoading}
                    >
                      {isLoading ? (
                        <>
                          <Loader2 size={12} className="animate-spin" />
                          生成中...
                        </>
                      ) : (
                        <>
                          下一题 →
                        </>
                      )}
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full h-8 text-xs text-gray-500"
                    onClick={() => {
                      reset()
                    }}
                  >
                    <RefreshCw size={12} />
                    清空重做
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>

        {isSubmitting && (
          <div className="flex-shrink-0 px-5 py-2.5 border-t border-black/5 bg-blue-50/40">
            <div className="flex items-center gap-2 text-xs text-[#3370ff]">
              <Loader2 size={12} className="animate-spin" />
              AI 正在评判你的答案...
            </div>
          </div>
        )}
      </aside>

      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0.5; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
    </>
  )
}
