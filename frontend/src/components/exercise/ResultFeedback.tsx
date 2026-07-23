import { useState } from 'react'
import { CheckCircle2, XCircle, AlertCircle, Lightbulb, BookOpen, ChevronDown, ChevronUp, Award } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import type { EvaluationResult } from '@/types/exercise'
import { cn } from '@/lib/utils'
import { LiquidGlassCard } from '@/components/ui/liquid-glass-card'

interface ResultFeedbackProps {
  result: EvaluationResult
  referenceSolution?: string | null
  exerciseType?: string
}

/** 代码题（主观题）的评分等级 */
function getScoreGrade(score: number): { label: string; color: string; icon: typeof Award } {
  if (score >= 90) return { label: '优秀', color: 'text-green-600', icon: Award }
  if (score >= 80) return { label: '良好', color: 'text-green-500', icon: Award }
  if (score >= 60) return { label: '及格', color: 'text-amber-500', icon: Award }
  return { label: '需改进', color: 'text-red-500', icon: Award }
}

export function ResultFeedback({ result, referenceSolution, exerciseType }: ResultFeedbackProps) {
  const passed = result.passed
  const score = result.score
  const [showAnswer, setShowAnswer] = useState(false)

  // 代码题（modification/creation/project）是主观题，用评分等级替代二元对错
  const isCodeExercise = ['modification', 'creation', 'project'].includes(exerciseType || '')

  const scoreColor = score >= 80 ? 'text-green-500' : score >= 60 ? 'text-amber-500' : 'text-red-500'
  const scoreBg = score >= 80 ? 'from-green-500/10' : score >= 60 ? 'from-amber-500/10' : 'from-red-500/10'

  const hasReference = referenceSolution && referenceSolution.trim().length > 0

  // 代码题：评分等级展示；理解题：保持二元对错
  const grade = isCodeExercise ? getScoreGrade(score) : null
  const GradeIcon = grade?.icon

  return (
    <div
      className={cn(
        'rounded-2xl border p-4 animate-in fade-in slide-in-from-top-2 duration-300',
        isCodeExercise
          ? score >= 60
            ? 'bg-gradient-to-br from-blue-50/60 to-indigo-50/30 border-blue-200/50'
            : 'bg-gradient-to-br from-orange-50/60 to-amber-50/30 border-orange-200/50'
          : passed
            ? 'bg-gradient-to-br from-green-50/80 to-emerald-50/40 border-green-200/60'
            : 'bg-gradient-to-br from-red-50/80 to-orange-50/40 border-red-200/60'
      )}
    >
      <div className="flex items-start gap-3 mb-3">
        <div
          className={cn(
            'w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm',
            isCodeExercise
              ? score >= 80
                ? 'bg-green-500/15 text-green-600'
                : score >= 60
                  ? 'bg-amber-500/15 text-amber-600'
                  : 'bg-red-500/15 text-red-600'
              : passed
                ? 'bg-green-500/15 text-green-600'
                : 'bg-red-500/15 text-red-600'
          )}
        >
          {isCodeExercise && GradeIcon
            ? <GradeIcon size={22} />
            : passed
              ? <CheckCircle2 size={22} />
              : <XCircle size={22} />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-base">
              {isCodeExercise && grade
                ? `代码评分：${grade.label}`
                : passed
                  ? '回答正确'
                  : '回答错误'}
            </span>
            <span className={cn('text-lg font-bold', isCodeExercise ? scoreColor : scoreColor)}>
              {score}<span className="text-xs font-normal text-gray-400">分</span>
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-0.5">
            {isCodeExercise ? `综合评分 ${score}/100` : `结果：${result.result}`}
          </div>
        </div>
      </div>

      <div className={cn('rounded-xl bg-gradient-to-br to-transparent p-3 mb-3', scoreBg)}>
        <div className="text-xs font-medium text-gray-600 mb-1.5 flex items-center gap-1.5">
          <AlertCircle size={12} />
          反馈解析
        </div>
        <div className="text-sm text-gray-700 leading-relaxed prose prose-sm max-w-none [&_p]:my-1.5 [&_code]:px-1 [&_code]:py-0.5 [&_code]:bg-black/5 [&_code]:rounded [&_code]:text-[0.9em] [&_code]:font-mono [&_pre]:bg-gray-900 [&_pre]:text-gray-100 [&_pre]:p-2.5 [&_pre]:rounded-lg [&_pre]:text-xs [&_pre]:overflow-x-auto">
          <ReactMarkdown>{result.feedback || '暂无反馈'}</ReactMarkdown>
        </div>
      </div>

      {hasReference && (
        <div className="mb-3">
          <button
            onClick={() => setShowAnswer(v => !v)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-blue-50/60 hover:bg-blue-50/80 text-blue-600 text-xs font-medium transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <BookOpen size={12} />
              查看参考答案
            </span>
            {showAnswer ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {showAnswer && (
            <div className="mt-2" style={{ animation: 'fadeInDown 0.2s ease forwards' }}>
              <LiquidGlassCard className="rounded-xl overflow-hidden" displacementScale={4}>
                <div className="px-3 py-1.5 border-b border-black/5 bg-emerald-50/50 text-[11px] text-emerald-700 font-medium flex items-center gap-1.5">
                  <BookOpen size={11} />
                  参考答案
                </div>
                <pre className="p-3 text-xs font-mono text-gray-700 whitespace-pre-wrap overflow-x-auto bg-black/2 max-h-60 overflow-y-auto">
                  {referenceSolution}
                </pre>
              </LiquidGlassCard>
            </div>
          )}
        </div>
      )}

      {result.needs_reteach && (
        <div className="flex items-start gap-2 p-3 bg-amber-50/80 rounded-xl border border-amber-200/50">
          <Lightbulb size={16} className="text-amber-500 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-amber-700 leading-relaxed">
            建议重新学习相关知识点，巩固基础后再继续练习。
          </div>
        </div>
      )}

      <style>{`
        @keyframes fadeInDown {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
