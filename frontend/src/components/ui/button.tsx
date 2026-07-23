import * as React from 'react'
import { cn } from '@/lib/utils'

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'ghost' | 'outline' | 'primary'
  size?: 'sm' | 'md' | 'lg' | 'icon'
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'md', ...props }, ref) => {
    const variants = {
      default: 'bg-white/80 hover:bg-white text-gray-800 border border-gray-200/80',
      ghost: 'bg-transparent hover:bg-black/5 text-gray-600 border-transparent',
      outline: 'bg-transparent hover:bg-black/5 text-gray-700 border border-gray-200',
      primary: 'bg-gradient-to-br from-[#3370ff] to-[#5e8bff] text-white border-transparent hover:from-[#2860e1] hover:to-[#4d7aff] shadow-lg shadow-blue-500/20',
    }

    const sizes = {
      sm: 'h-7 px-3 text-xs rounded-md',
      md: 'h-9 px-4 text-sm rounded-lg',
      lg: 'h-11 px-6 text-base rounded-xl',
      icon: 'h-9 w-9 rounded-lg',
    }

    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-1.5 font-medium transition-all duration-200',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30',
          'disabled:opacity-50 disabled:pointer-events-none',
          'active:scale-[0.98]',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'

export { Button }
