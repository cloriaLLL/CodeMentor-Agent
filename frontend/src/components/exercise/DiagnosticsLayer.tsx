/**
 * CodeMentor Agent — 诊断层组件
 *
 * 在 CodeEditor 上叠加错误下划线层（pointer-events:none）。
 * 根据诊断信息的 line/column 渲染下划线，颜色按 severity 区分。
 *
 * 设计：纯展示组件，不处理交互；通过 syncScrollProps 接收滚动位移，
 * 与 textarea 同步滚动，确保下划线与代码对齐。
 *
 * 依据：DOC-05 §6.4 前端编辑器增强
 */
import type { Diagnostic } from '../../hooks/useLanguageService'

interface DiagnosticsLayerProps {
  /** 诊断列表 */
  diagnostics: Diagnostic[]
  /** 字体大小（与 textarea 一致，用于定位计算） */
  fontSize?: number
  /** 行高（与 textarea 一致，像素值） */
  lineHeight?: number
  /** textarea 滚动位移（用于同步滚动） */
  scrollTop?: number
  scrollLeft?: number
}

const SEVERITY_COLOR: Record<string, string> = {
  error: '#f38ba8',
  warning: '#fab387',
  info: '#89b4fa',
  hint: '#a6adc8',
}

/** 编辑器内边距（与 textarea/pre 的 p-4 一致） */
const EDITOR_PADDING = 16

export function DiagnosticsLayer({
  diagnostics,
  fontSize = 13,
  lineHeight = 20.8,   // 1.6 * 13 ≈ 20.8
  scrollTop = 0,
  scrollLeft = 0,
}: DiagnosticsLayerProps) {
  const charWidth = fontSize * 0.6
  return (
    <div
      className="absolute inset-0 m-0 p-4 font-mono text-[13px] pointer-events-none whitespace-pre overflow-hidden"
      style={{ lineHeight: `${lineHeight}px` }}
    >
      {diagnostics.map((d, idx) => {
        // 计算 span 位置：line*lineHeight 减去滚动位移 + padding
        const top = (d.line - 1) * lineHeight + EDITOR_PADDING - scrollTop
        const left = (d.column - 1) * charWidth + EDITOR_PADDING - scrollLeft
        const endCol = d.end_column || d.column + 1
        const width = (endCol - d.column) * charWidth
        const color = SEVERITY_COLOR[d.severity] || SEVERITY_COLOR.error
        // 若 span 完全在可视区外，跳过渲染（性能优化）
        if (top + lineHeight < 0 || top > 1000) return null
        return (
          <span
            key={`${d.line}:${d.column}:${d.error_code}:${idx}`}
            className="absolute"
            style={{
              top: `${top}px`,
              left: `${left}px`,
              width: `${Math.max(width, 8)}px`,
              height: `${lineHeight}px`,
              // 使用 text-decoration 的 wavy 下划线（border 不支持 wavy）
              textDecoration: `underline wavy ${color}`,
              textUnderlineOffset: '100%',
              textDecorationThickness: '2px',
              opacity: 0.85,
            }}
            title={d.message}
          />
        )
      })}
    </div>
  )
}
