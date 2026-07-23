import { useState, useEffect } from 'react'
import { Check, X, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useExercise } from '@/contexts/ExerciseContext'
import { cn } from '@/lib/utils'
import type { ExerciseData } from '@/types/exercise'

interface ChoiceQuestionProps {
  exercise: ExerciseData
}

export function ChoiceQuestion({ exercise }: ChoiceQuestionProps) {
  const { submitAnswer, isSubmitting, result } = useExercise()
  const [selected, setSelected] = useState<string>('')
  const [multiSelected, setMultiSelected] = useState<Set<string>>(new Set())
  const [fillAnswer, setFillAnswer] = useState('')
  const [textAnswer, setTextAnswer] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const subtype = exercise.subtype || 'choice'
  const hasOptions = exercise.options && exercise.options.length > 0
  const isMulti = subtype === 'choice' && hasOptions && exercise.options!.length > 4 &&
    exercise.question.includes('多选')

  const correctAnswers = exercise.correct_answer
    ? new Set(exercise.correct_answer.split(',').map(a => a.trim().toUpperCase()))
    : null

  const isCorrectOption = (key: string) => correctAnswers?.has(key) ?? false
  const isUserWrong = (key: string) => {
    if (!submitted || !correctAnswers) return false
    if (isMulti) return multiSelected.has(key) && !correctAnswers.has(key)
    return selected === key && !correctAnswers.has(key)
  }
  const isUserRight = (key: string) => {
    if (!submitted || !correctAnswers) return false
    if (isMulti) return multiSelected.has(key) && correctAnswers.has(key)
    return selected === key && correctAnswers.has(key)
  }

  useEffect(() => {
    setSelected('')
    setMultiSelected(new Set())
    setFillAnswer('')
    setTextAnswer('')
    setSubmitted(false)
  }, [exercise.exercise_id])

  const handleSubmit = async () => {
    let answer: string
    if (subtype === 'fillblank') {
      answer = fillAnswer.trim()
    } else if (isMulti) {
      answer = Array.from(multiSelected).sort().join(',')
    } else if (hasOptions) {
      answer = selected
    } else {
      answer = textAnswer.trim()
    }
    if (!answer) return
    setSubmitted(true)
    await submitAnswer(answer)
  }

  const handleToggleMulti = (key: string) => {
    if (submitted) return
    setMultiSelected(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  if (subtype === 'fillblank') {
    return (
      <div className="space-y-3">
        <input
          type="text"
          value={fillAnswer}
          onChange={e => !submitted && setFillAnswer(e.target.value)}
          placeholder="输入你的答案..."
          disabled={submitted}
          className="w-full h-11 px-4 text-sm bg-white/80 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500/40 transition-all"
          onKeyDown={e => {
            if (e.key === 'Enter' && fillAnswer.trim() && !submitted) handleSubmit()
          }}
        />
        <Button
          variant="primary"
          className="w-full h-10"
          disabled={!fillAnswer.trim() || submitted || isSubmitting}
          onClick={handleSubmit}
        >
          {isSubmitting ? '评判中...' : submitted ? '已提交' : '提交答案'}
          {!submitted && !isSubmitting && <Send size={14} />}
        </Button>
      </div>
    )
  }

  if (subtype === 'truefalse') {
    const correctKey = correctAnswers?.has('T') ? 'T' : correctAnswers?.has('F') ? 'F' : null
    const userWrongChoice = submitted && correctKey && selected && selected !== correctKey
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          {[
            { key: 'T', label: '正确', color: 'green' },
            { key: 'F', label: '错误', color: 'red' },
          ].map(opt => {
            const isSelected = selected === opt.key
            const isCorrect = correctKey === opt.key
            const showCorrect = submitted && isCorrect
            const showWrong = submitted && isSelected && !isCorrect
            return (
              <button
                key={opt.key}
                disabled={submitted}
                onClick={() => setSelected(opt.key)}
                className={cn(
                  'h-14 rounded-xl border-2 flex flex-col items-center justify-center gap-1 transition-all',
                  'font-medium text-sm',
                  showWrong
                    ? 'bg-red-50/80 border-red-400 text-red-600 shadow-md shadow-red-500/10'
                    : showCorrect
                    ? 'bg-green-50/80 border-green-400 text-green-600 shadow-md shadow-green-500/10'
                    : isSelected
                    ? opt.color === 'green'
                      ? 'bg-green-50/80 border-green-400 text-green-600 shadow-md shadow-green-500/10'
                      : 'bg-red-50/80 border-red-400 text-red-600 shadow-md shadow-red-500/10'
                    : 'bg-white/60 border-gray-200 text-gray-600 hover:border-gray-300',
                  submitted && !isSelected && !isCorrect && 'opacity-50'
                )}
              >
                <span className="text-lg font-bold">{opt.label}</span>
              </button>
            )
          })}
        </div>
        <Button
          variant="primary"
          className="w-full h-10"
          disabled={!selected || submitted || isSubmitting}
          onClick={handleSubmit}
        >
          {isSubmitting ? '评判中...' : submitted ? '已提交' : '提交答案'}
          {!submitted && !isSubmitting && <Send size={14} />}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {!hasOptions ? (
        <>
          <textarea
            value={textAnswer}
            onChange={e => !submitted && setTextAnswer(e.target.value)}
            placeholder="在此输入你的答案或思考过程..."
            disabled={submitted}
            className="w-full min-h-[160px] p-4 text-sm bg-white/80 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500/40 transition-all resize-none leading-relaxed"
          />
          <Button
            variant="primary"
            className="w-full h-10"
            disabled={!textAnswer.trim() || submitted || isSubmitting}
            onClick={handleSubmit}
          >
            {isSubmitting ? '评判中...' : submitted ? '已提交' : '提交答案'}
            {!submitted && !isSubmitting && <Send size={14} />}
          </Button>
        </>
      ) : (
        <>
          {exercise.options?.map((opt, idx) => {
            const key = String.fromCharCode(65 + idx)
            const isSelected = isMulti ? multiSelected.has(key) : selected === key
            const correct = isCorrectOption(key)
            const userWrong = isUserWrong(key)
            const userRight = isUserRight(key)
            const showCorrectBadge = submitted && correct
            const showWrongBadge = userWrong
            return (
              <button
                key={idx}
                disabled={submitted}
                onClick={() => isMulti ? handleToggleMulti(key) : setSelected(key)}
                className={cn(
                  'w-full text-left p-3 rounded-xl border transition-all flex items-center gap-3',
                  'group hover:border-blue-300',
                  showWrongBadge
                    ? 'bg-red-50/70 border-red-400 shadow-sm shadow-red-500/5'
                    : showCorrectBadge
                    ? 'bg-green-50/70 border-green-400 shadow-sm shadow-green-500/5'
                    : isSelected
                    ? 'bg-blue-50/70 border-blue-400 shadow-sm shadow-blue-500/5'
                    : 'bg-white/60 border-gray-200',
                  submitted && !isSelected && !correct && 'opacity-60'
                )}
              >
                <div
                  className={cn(
                    'w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0 transition-colors',
                    showWrongBadge
                      ? 'bg-gradient-to-br from-red-500 to-red-600 text-white'
                      : showCorrectBadge
                      ? 'bg-gradient-to-br from-green-500 to-green-600 text-white'
                      : isSelected
                      ? 'bg-gradient-to-br from-[#3370ff] to-[#5e8bff] text-white'
                      : 'bg-gray-100 text-gray-500 group-hover:bg-gray-200'
                  )}
                >
                  {key}
                </div>
                <span className="flex-1 text-sm text-gray-700">{opt}</span>
                {showWrongBadge && <X size={16} className="text-red-500 flex-shrink-0" />}
                {showCorrectBadge && <Check size={16} className="text-green-500 flex-shrink-0" />}
                {!submitted && isSelected && <Check size={16} className="text-[#3370ff] flex-shrink-0" />}
              </button>
            )
          })}
          <Button
            variant="primary"
            className="w-full h-10 mt-3"
            disabled={(isMulti ? multiSelected.size === 0 : !selected) || submitted || isSubmitting}
            onClick={handleSubmit}
          >
            {isSubmitting ? '评判中...' : submitted ? '已提交' : '提交答案'}
            {!submitted && !isSubmitting && <Send size={14} />}
          </Button>
        </>
      )}
    </div>
  )
}
