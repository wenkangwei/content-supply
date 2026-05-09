import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  FileText,
  Rss,
  Globe,
  Flame,
  PenLine,
  Trash2,
  Settings,
  Database,
} from 'lucide-react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: '仪表板' },
  { to: '/items', icon: FileText, label: '内容池' },
  { to: '/feeds', icon: Rss, label: '订阅源' },
  { to: '/crawl', icon: Globe, label: '爬取中心' },
  { to: '/hot', icon: Flame, label: '热搜监控' },
  { to: '/rewrite', icon: PenLine, label: '内容改写' },
  { to: '/cleanup', icon: Trash2, label: '清理管理' },
  { to: '/settings', icon: Settings, label: '设置' },
]

export function Sidebar() {
  return (
    <aside className="hidden w-52 shrink-0 border-r border-border bg-bg-sidebar md:flex md:flex-col">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <Database className="h-5 w-5 text-accent" />
        <span className="text-sm font-semibold text-text-primary">Content Supply</span>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? 'bg-accent/10 text-accent'
                  : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
              }`
            }
          >
            <Icon className="h-4 w-4" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-border p-3 text-xs text-text-muted">
        v1.0.0
      </div>
    </aside>
  )
}
