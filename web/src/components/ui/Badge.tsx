interface Props {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  children: React.ReactNode
}

const variants = {
  default: 'bg-bg-tertiary text-text-secondary',
  success: 'bg-success/10 text-success',
  warning: 'bg-warning/10 text-warning',
  danger: 'bg-danger/10 text-danger',
  info: 'bg-accent/10 text-accent',
}

export function Badge({ variant = 'default', children }: Props) {
  return (
    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${variants[variant]}`}>
      {children}
    </span>
  )
}
