import React, { createContext, useContext, useState, useCallback, useRef } from 'react'
import type {
  ExerciseData,
  EvaluationResult,
  ExerciseType,
} from '@/types/exercise'
import type { Message } from '@/types'
import { exerciseApi } from '@/lib/exercise-api'
import { useChat } from './ChatContext'
import { generateId } from '@/lib/utils'

interface GenerateParams {
  exercise_type: ExerciseType
  knowledge_point: string
  difficulty?: string
  subtype?: string
  session_id?: string
  language?: string
}

interface ExerciseContextValue {
  exercise: ExerciseData | null
  result: EvaluationResult | null
  isLoading: boolean
  isSubmitting: boolean
  isFetchingHint: boolean
  hint: string | null
  error: string | null
  panelOpen: boolean
  lastGenerateParams: GenerateParams | null

  openPanel: () => void
  closePanel: () => void

  generateExercise: (params: GenerateParams) => Promise<void>
  generateNext: () => Promise<void>

  setExerciseFromChat: (params: {
    question: string
    starter_code?: string
    test_cases?: string
    exercise_type?: ExerciseType
    language?: string
  }) => void

  openCodeEditor: (code: string, language?: string) => void

  submitAnswer: (userAnswer: string) => Promise<void>

  updateExercise: (patch: Partial<ExerciseData>) => void

  fetchHint: () => Promise<void>
  clearHint: () => void

  reset: () => void
  clearError: () => void
}

const ExerciseContext = createContext<ExerciseContextValue | null>(null)

export function ExerciseProvider({ children }: { children: React.ReactNode }) {
  const [exercise, setExercise] = useState<ExerciseData | null>(null)
  const [result, setResult] = useState<EvaluationResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isFetchingHint, setIsFetchingHint] = useState(false)
  const [hint, setHint] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [panelOpen, setPanelOpen] = useState(false)
  const [lastGenerateParams, setLastGenerateParams] = useState<GenerateParams | null>(null)
  const fetchingHintRef = useRef(false)

  const chat = useChat()

  const openPanel = useCallback(() => setPanelOpen(true), [])
  const closePanel = useCallback(() => setPanelOpen(false), [])
  const clearError = useCallback(() => setError(null), [])
  const clearHint = useCallback(() => setHint(null), [])

  const addResultToChat = useCallback((exercise: ExerciseData, userAnswer: string, result: EvaluationResult) => {
    if (!chat.currentChatId) return
    if (exercise.source !== 'chat') return

    const userMsg: Message = {
      id: generateId(),
      role: 'user',
      content: `【练习提交】\n\n题目：${exercise.question.slice(0, 100)}${exercise.question.length > 100 ? '…' : ''}\n\n我的答案：\n\`\`\`${exercise.language || 'python'}\n${userAnswer}\n\`\`\``,
      timestamp: new Date().toISOString(),
    }
    chat.dispatch({ type: 'ADD_MESSAGE', payload: { chatId: chat.currentChatId, message: userMsg } })

    const scoreLabel = result.passed ? '✅ 通过' : '❌ 未通过'
    const feedbackText = result.feedback || (result.passed ? '做得不错！继续保持。' : '还需要加把劲，建议复习相关知识点。')

    const aiMsg: Message = {
      id: generateId(),
      role: 'assistant',
      content: `**练习结果：${scoreLabel}（${result.score}分）**\n\n${feedbackText}\n\n${result.passed ? '🎉 恭喜你完成了这道练习！掌握得不错，我们可以继续学习下一个知识点，或者你想再挑战一道同类型的题目吗？' : '💪 没关系，学习就是不断试错的过程。建议你重新回顾一下相关知识点，理解原理后再尝试一次。需要我帮你讲解这道题的思路吗？'}`,
      timestamp: new Date().toISOString(),
    }
    chat.dispatch({ type: 'ADD_MESSAGE', payload: { chatId: chat.currentChatId, message: aiMsg } })
  }, [chat])

  const generateExercise = useCallback(async (params: GenerateParams) => {
    setIsLoading(true)
    setError(null)
    setResult(null)
    setHint(null)
    setPanelOpen(true)
    setExercise(null)
    setLastGenerateParams(params)
    try {
      const data = await exerciseApi.generate(params)
      setExercise({ ...data, source: 'launcher' })
    } catch (e) {
      setError(e instanceof Error ? e.message : '生成题目失败')
    } finally {
      setIsLoading(false)
    }
  }, [])

  const generateNext = useCallback(async () => {
    if (!lastGenerateParams) return
    await generateExercise(lastGenerateParams)
  }, [lastGenerateParams, generateExercise])

  const setExerciseFromChat = useCallback((params: {
    question: string
    starter_code?: string
    test_cases?: string
    exercise_type?: ExerciseType
    language?: string
  }) => {
    const type: ExerciseType = params.starter_code ? 'creation' : 'understanding'
    const subtype = !params.starter_code ? 'choice' : undefined
    const lang = params.language || 'python'
    setExercise({
      exercise_id: generateId(),
      exercise_type: params.exercise_type || type,
      subtype: params.exercise_type ? undefined : subtype,
      question: params.question,
      options: null,
      starter_code: params.starter_code || null,
      test_cases: params.test_cases || null,
      modification_requirement: null,
      acceptance_criteria: null,
      evaluation_dimensions: null,
      difficulty: 'Medium',
      knowledge_points: [],
      estimated_time_min: 10,
      language: lang,
      source: 'chat',
    })
    setResult(null)
    setHint(null)
    setError(null)
    setPanelOpen(true)
  }, [])

  const openCodeEditor = useCallback((code: string, language?: string) => {
    setExercise({
      exercise_id: generateId(),
      exercise_type: 'creation',
      subtype: undefined,
      question: '自由代码练习 - 编写、运行并测试你的代码',
      options: null,
      starter_code: code,
      test_cases: null,
      modification_requirement: null,
      acceptance_criteria: null,
      evaluation_dimensions: null,
      difficulty: 'Medium',
      knowledge_points: [],
      estimated_time_min: 0,
      language: language || 'python',
      source: 'chat',
    })
    setResult(null)
    setHint(null)
    setError(null)
    setPanelOpen(true)
  }, [])

  const submitAnswer = useCallback(async (userAnswer: string) => {
    if (!exercise || !userAnswer.trim()) return
    setIsSubmitting(true)
    setError(null)
    setResult(null)
    try {
      const res = await exerciseApi.submit({
        exercise_type: exercise.exercise_type,
        question: exercise.question,
        options: exercise.options ?? null,
        correct_answer: exercise.correct_answer ?? null,
        explanation: exercise.explanation ?? null,
        starter_code: exercise.starter_code ?? null,
        reference_solution: exercise.reference_solution ?? null,
        test_cases: exercise.test_cases ?? null,
        modification_requirement: exercise.modification_requirement ?? null,
        acceptance_criteria: exercise.acceptance_criteria ?? null,
        evaluation_dimensions: exercise.evaluation_dimensions ?? null,
        difficulty: exercise.difficulty,
        knowledge_points: exercise.knowledge_points,
        subtype: exercise.subtype ?? null,
        user_answer: userAnswer,
        language: exercise.language || 'python',
      })
      setResult(res)
      addResultToChat(exercise, userAnswer, res)
    } catch (e) {
      setError(e instanceof Error ? e.message : '提交答案失败')
    } finally {
      setIsSubmitting(false)
    }
  }, [exercise, addResultToChat])

  const updateExercise = useCallback((patch: Partial<ExerciseData>) => {
    setExercise((prev) => (prev ? { ...prev, ...patch } : prev))
  }, [])

  const fetchHint = useCallback(async () => {
    if (!exercise || fetchingHintRef.current) return
    fetchingHintRef.current = true
    setIsFetchingHint(true)
    setError(null)
    try {
      const hintPrompt = `针对以下题目，给学习者一个简短的提示（不超过100字），引导思路但不要直接给出答案：

题目类型：${exercise.exercise_type}
题目：${exercise.question}
${exercise.modification_requirement ? `修改需求：${exercise.modification_requirement}` : ''}

请直接输出提示内容，不要前缀。`

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: hintPrompt, history: [] }),
      })
      if (!res.ok) throw new Error(`获取提示失败: ${res.status}`)
      const data = await res.json()
      setHint(data.reply || '暂无提示')
    } catch {
      setHint('获取提示失败，请稍后重试')
    } finally {
      fetchingHintRef.current = false
      setIsFetchingHint(false)
    }
  }, [exercise])

  const reset = useCallback(() => {
    setExercise(null)
    setResult(null)
    setHint(null)
    setError(null)
    setIsLoading(false)
    setIsSubmitting(false)
    setIsFetchingHint(false)
  }, [])

  const value: ExerciseContextValue = {
    exercise,
    result,
    isLoading,
    isSubmitting,
    isFetchingHint,
    hint,
    error,
    panelOpen,
    lastGenerateParams,
    openPanel,
    closePanel,
    generateExercise,
    generateNext,
    setExerciseFromChat,
    openCodeEditor,
    submitAnswer,
    updateExercise,
    fetchHint,
    clearHint,
    reset,
    clearError,
  }

  return <ExerciseContext.Provider value={value}>{children}</ExerciseContext.Provider>
}

export function useExercise() {
  const ctx = useContext(ExerciseContext)
  if (!ctx) throw new Error('useExercise must be used within ExerciseProvider')
  return ctx
}
