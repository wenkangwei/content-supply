interface Props {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md'
  disabled?: boolean
  onClick?: () => void
  children: React.ReactNode
}

const variantClasses = {
  primary: 'bg-accent text-white hover:bg-accent-hover',
  secondary: 'border border-border bg-bg-secondary text-text-primary hover:bg-bg-hover',
  danger: 'bg-danger text-white hover:bg-red-600',
  ghost: 'text-text-secondary hover:text-text-primary hover:bg-bg-hover',
}

const sizeClasses = {
  sm: 'px-2.5 py-1 text-xs',
  md: 'px-4 py-2 text-sm',
}

export function Button({ variant = 'primary', size = 'md', disabled, onClick, children }: Props) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-colors disabled:opacity-50 ${variantClasses[variant]} ${sizeClasses[size]}`}
    >
      {children}
    </button>
  )
}
