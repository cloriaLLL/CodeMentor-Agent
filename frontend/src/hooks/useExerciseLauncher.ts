import { useMemo } from 'react'
import { useExercise } from '@/contexts/ExerciseContext'
import type { ExerciseType, UnderstandingSubtype } from '@/types/exercise'

interface ParsedExerciseRequest {
  exercise_type: ExerciseType
  knowledge_point: string
  difficulty?: string
  subtype?: UnderstandingSubtype
}

const DEFAULT_DIFFICULTY = 'Medium'

export function useExerciseLauncher() {
  const { generateExercise, openPanel, panelOpen } = useExercise()

  const launch = useMemo(() => {
    return (params: ParsedExerciseRequest) => {
      generateExercise({
        exercise_type: params.exercise_type,
        knowledge_point: params.knowledge_point,
        difficulty: params.difficulty || DEFAULT_DIFFICULTY,
        subtype: params.subtype,
      })
    }
  }, [generateExercise])

  const open = openPanel

  return { launch, open, panelOpen }
}

export function detectExerciseRequest(text: string): ParsedExerciseRequest | null {
  const lower = text.toLowerCase()

  if (lower.includes('练习') || lower.includes('题目') || lower.includes('做一道')) {
    let type: ExerciseType = 'understanding'
    let subtype: UnderstandingSubtype | undefined

    if (lower.includes('选择题') || lower.includes('单选')) {
      type = 'understanding'
      subtype = 'choice'
    } else if (lower.includes('判断题')) {
      type = 'understanding'
      subtype = 'truefalse'
    } else if (lower.includes('填空题')) {
      type = 'understanding'
      subtype = 'fillblank'
    } else if (lower.includes('修改') || lower.includes('改代码')) {
      type = 'modification'
    } else if (lower.includes('编写') || lower.includes('实现') || lower.includes('从零')) {
      type = 'creation'
    } else if (lower.includes('项目') || lower.includes('综合')) {
      type = 'project'
    }

    const difficultyMatch = text.match(/(简单|easy|入门|中等|medium|进阶|困难|hard|高级)/i)
    let difficulty = DEFAULT_DIFFICULTY
    if (difficultyMatch) {
      const d = difficultyMatch[1].toLowerCase()
      if (['简单', 'easy', '入门'].includes(d)) difficulty = 'Easy'
      else if (['中等', 'medium', '进阶'].includes(d)) difficulty = 'Medium'
      else if (['困难', 'hard', '高级'].includes(d)) difficulty = 'Hard'
    }

    const knowledgePoint = text
      .replace(/帮我|请|生成|来一道|做一道|练习|题目|关于|的|选择题|判断题|填空题|修改题|编写题|项目题|简单|中等|困难|easy|medium|hard/g, '')
      .trim()
      .slice(0, 50) || 'Python基础'

    return { exercise_type: type, knowledge_point: knowledgePoint, difficulty, subtype }
  }

  return null
}
