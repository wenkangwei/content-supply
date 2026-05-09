import { Search, Bell, Wifi } from 'lucide-react'
import { useAppStore } from '@/stores/useAppStore'

export function Header() {
  const { sidebarCollapsed, toggleSidebar } = useAppStore()

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-bg-secondary px-6">
      <div className="flex items-center gap-4">
        <button
          onClick={toggleSidebar}
          className="text-text-secondary hover:text-text-primary md:hidden"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={sidebarCollapsed ? 'M4 6h16M4 12h16M4 18h16' : 'M6 18L18 6M6 6l12 12'} />
          </svg>
        </button>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder="搜索内容..."
            className="h-8 w-64 rounded-md border border-border bg-bg-primary pl-9 pr-3 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1 text-xs text-success">
          <Wifi className="h-3 w-3" />
          <span>已连接</span>
        </div>
        <button className="text-text-secondary hover:text-text-primary">
          <Bell className="h-4 w-4" />
        </button>
      </div>
    </header>
  )
}
