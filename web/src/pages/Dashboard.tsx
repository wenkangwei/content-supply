import { useEffect, useState } from 'react'
import { FileText, Rss, Globe, Flame, TrendingUp } from 'lucide-react'
import { getItemCount } from '@/api/items'
import { getFeeds } from '@/api/feeds'
import { getHotKeywords } from '@/api/hot'
import { Spinner } from '@/components/ui/Spinner'

interface Stats {
  totalItems: number
  publishedItems: number
  totalFeeds: number
  activeFeeds: number
  hotKeywords: number
  loading: boolean
}

export function Dashboard() {
  const [stats, setStats] = useState<Stats>({
    totalItems: 0, publishedItems: 0, totalFeeds: 0, activeFeeds: 0, hotKeywords: 0, loading: true,
  })

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [itemsAll, itemsPub, feeds, hot] = await Promise.allSettled([
          getItemCount(),
          getItemCount({ status: 'published' }),
          getFeeds({ limit: 500 }),
          getHotKeywords({ limit: 1 }),
        ])
        setStats({
          totalItems: itemsAll.status === 'fulfilled' ? (itemsAll.value as { total: number }).total : 0,
          publishedItems: itemsPub.status === 'fulfilled' ? (itemsPub.value as { total: number }).total : 0,
          totalFeeds: feeds.status === 'fulfilled' ? (feeds.value as unknown[]).length : 0,
          activeFeeds: feeds.status === 'fulfilled'
            ? (feeds.value as { status: string }[]).filter((f) => f.status === 'active').length : 0,
          hotKeywords: hot.status === 'fulfilled' ? (hot.value as unknown[]).length : 0,
          loading: false,
        })
      } catch {
        setStats((s) => ({ ...s, loading: false }))
      }
    }
    fetchStats()
  }, [])

  if (stats.loading) return <Spinner className="py-20" />

  const cards = [
    { label: '内容总数', value: stats.totalItems, icon: FileText, color: 'text-accent', bg: 'bg-accent/10' },
    { label: '已发布', value: stats.publishedItems, icon: TrendingUp, color: 'text-success', bg: 'bg-success/10' },
    { label: '订阅源', value: stats.totalFeeds, icon: Rss, color: 'text-warning', bg: 'bg-warning/10' },
    { label: '活跃源', value: stats.activeFeeds, icon: Globe, color: 'text-success', bg: 'bg-success/10' },
    { label: '热搜词', value: stats.hotKeywords, icon: Flame, color: 'text-danger', bg: 'bg-danger/10' },
  ]

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-8 text-2xl font-bold text-text-primary">仪表板</h1>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {cards.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="rounded-xl border border-border bg-bg-secondary p-5">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs text-text-muted">{label}</span>
              <div className={`rounded-lg p-1.5 ${bg}`}>
                <Icon className={`h-4 w-4 ${color}`} />
              </div>
            </div>
            <p className="text-3xl font-bold text-text-primary">{value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
