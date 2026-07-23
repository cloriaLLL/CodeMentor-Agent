import * as React from 'react'
import { cn } from '@/lib/utils'

export interface LiquidGlassCardProps
  extends React.HTMLAttributes<HTMLDivElement> {
  displacementScale?: number
  blur?: number
  interactive?: boolean
}

export const LiquidGlassCard = React.forwardRef<
  HTMLDivElement,
  LiquidGlassCardProps
>(
  (
    {
      className,
      displacementScale = 12,
      blur = 16,
      interactive = true,
      children,
      ...props
    },
    ref
  ) => {
    const [chromiumRefract, setChromiumRefract] = React.useState(false)
    const [mouse, setMouse] = React.useState({ x: 50, y: 50 })

    React.useEffect(() => {
      const svg = document.getElementById(`lg-filter-${displacementScale}`)
      const supportsUrlInBackdrop =
        CSS.supports('backdrop-filter', 'url(#x)') ||
        CSS.supports('-webkit-backdrop-filter', 'url(#x)')
      const isReducedMotion = window.matchMedia(
        '(prefers-reduced-motion: reduce)'
      ).matches

      if (svg && svg.isConnected && supportsUrlInBackdrop && !isReducedMotion) {
        setChromiumRefract(true)
      }
    }, [displacementScale])

    const handleMouseMove = React.useCallback(
      (e: React.MouseEvent<HTMLDivElement>) => {
        if (!interactive) return
        const rect = e.currentTarget.getBoundingClientRect()
        const x = Math.max(
          0,
          Math.min(100, ((e.clientX - rect.left) / rect.width) * 100)
        )
        const y = Math.max(
          0,
          Math.min(100, ((e.clientY - rect.top) / rect.height) * 100)
        )
        setMouse({ x, y })
      },
      [interactive]
    )

    return (
      <div
        ref={ref}
        onMouseMove={handleMouseMove}
        className={cn(
          'relative overflow-hidden rounded-xl border border-white/80',
          'bg-white/75 shadow-[0_8px_32px_rgba(0,0,0,0.06)]',
          'before:absolute before:inset-0 before:rounded-xl before:pointer-events-none',
          'before:shadow-[inset_1px_1px_0_0_rgba(255,255,255,0.9),inset_-1px_-1px_0_0_rgba(255,255,255,0.3)]',
          className
        )}
        style={{
          backdropFilter: `blur(${blur}px) saturate(200%)`,
          WebkitBackdropFilter: `blur(${blur}px) saturate(200%)`,
          ['--mouse-x' as string]: `${mouse.x}%`,
          ['--mouse-y' as string]: `${mouse.y}%`,
        }}
        {...props}
      >
        {interactive && (
          <div
            aria-hidden
            className="absolute inset-0 rounded-xl pointer-events-none transition-opacity duration-300"
            style={{
              background: `radial-gradient(600px circle at var(--mouse-x) var(--mouse-y), rgba(51,112,255,0.06), transparent 40%)`,
            }}
          />
        )}

        {chromiumRefract && (
          <div
            aria-hidden
            className="absolute inset-0 rounded-xl pointer-events-none"
            style={{
              backdropFilter: `url(#lg-filter-${displacementScale}) blur(${blur}px) saturate(200%)`,
              WebkitBackdropFilter: `url(#lg-filter-${displacementScale}) blur(${blur}px) saturate(200%)`,
            }}
          />
        )}

        <div className="relative z-10">{children}</div>
      </div>
    )
  }
)
LiquidGlassCard.displayName = 'LiquidGlassCard'

export function LiquidGlassFilters() {
  return (
    <svg
      className="absolute w-0 h-0 pointer-events-none"
      aria-hidden
      style={{ position: 'absolute', width: 0, height: 0, overflow: 'hidden' }}
    >
      <defs>
        <filter id="lg-filter-12" colorInterpolationFilters="sRGB">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.008 0.008"
            numOctaves={2}
            seed={7}
            result="noise"
          />
          <feGaussianBlur in="noise" stdDeviation={2} result="smoothed" />
          <feDisplacementMap
            in="SourceGraphic"
            in2="smoothed"
            scale={12}
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
        <filter id="lg-filter-8" colorInterpolationFilters="sRGB">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.01 0.01"
            numOctaves={2}
            seed={3}
            result="noise"
          />
          <feGaussianBlur in="noise" stdDeviation={1.5} result="smoothed" />
          <feDisplacementMap
            in="SourceGraphic"
            in2="smoothed"
            scale={8}
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
      </defs>
    </svg>
  )
}
