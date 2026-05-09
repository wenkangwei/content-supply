import { useEffect, useState } from 'react'
import { Plus, RefreshCw, Trash2, ToggleLeft } from 'lucide-react'
import { getFeeds, createFeed, deleteFeed, toggleFeed } from '@/api/feeds'
import { triggerFeedCrawl } from '@/api/crawl'
import type { Feed, FeedCreate } from '@/api/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { formatDate } from '@/utils/format'
import { SOURCE_TYPE_LABELS } from '@/utils/constants'

export function Feeds() {
  const [feeds, setFeeds] = useState<Feed[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<FeedCreate>({ name: '', url: '', source_type: 'rss' })

  const fetchFeeds = async () => {
    setLoading(true)
    try { const data = await getFeeds({ limit: 500 }); setFeeds(data) }
    catch { setFeeds([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchFeeds() }, [])

  const handleCreate = async () => {
    await createFeed(form)
    setForm({ name: '', url: '', source_type: 'rss' })
    setShowForm(false)
    fetchFeeds()
  }

  const statusVariant = (s: string) => s === 'active' ? 'success' : s === 'error' ? 'danger' : 'warning'

  if (loading) return <Spinner className="py-20" />

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary">订阅源管理</h1>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="h-3.5 w-3.5" /> 添加源
        </Button>
      </div>

      {showForm && (
        <div className="mb-6 rounded-xl border border-border bg-bg-secondary p-5">
          <div className="grid gap-3 md:grid-cols-4">
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="名称" className="h-10 rounded-lg border border-border bg-bg-primary px-3 text-sm text-text-primary focus:border-accent focus:outline-none" />
            <input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="URL" className="h-10 rounded-lg border border-border bg-bg-primary px-3 text-sm text-text-primary focus:border-accent focus:outline-none" />
            <select value={form.source_type} onChange={(e) => setForm({ ...form, source_type: e.target.value as FeedCreate['source_type'] })} className="h-10 rounded-lg border border-border bg-bg-primary px-3 text-sm text-text-primary focus:border-accent focus:outline-none">
              <option value="rss">RSS</option>
              <option value="atom">Atom</option>
              <option value="web">Web</option>
            </select>
            <div className="flex gap-2">
              <Button size="sm" onClick={handleCreate} disabled={!form.name || !form.url}>创建</Button>
              <Button size="sm" variant="ghost" onClick={() => setShowForm(false)}>取消</Button>
            </div>
          </div>
        </div>
      )}

      {feeds.length === 0 ? (
        <EmptyState message="暂无订阅源" />
      ) : (
        <div className="space-y-2">
          {feeds.map((feed) => (
            <div key={feed.id} className="flex items-center justify-between rounded-xl border border-border bg-bg-secondary p-4">
              <div className="flex-1">
                <div className="mb-1 flex items-center gap-2">
                  <span className="text-sm font-medium text-text-primary">{feed.name}</span>
                  <Badge variant={statusVariant(feed.status)}>{feed.status}</Badge>
                  <Badge>{SOURCE_TYPE_LABELS[feed.source_type]}</Badge>
                </div>
                <div className="text-xs text-text-muted">
                  {feed.url} · 轮询 {feed.poll_interval}s · 上次: {formatDate(feed.last_fetched_at)}
                  {feed.error_count > 0 && <span className="ml-2 text-danger">错误 {feed.error_count} 次</span>}
                </div>
              </div>
              <div className="flex gap-1">
                <button onClick={async () => { await triggerFeedCrawl(feed.id); fetchFeeds() }} className="rounded-lg p-2 text-text-muted hover:text-accent hover:bg-bg-hover" title="立即爬取">
                  <RefreshCw className="h-4 w-4" />
                </button>
                <button onClick={async () => { await toggleFeed(feed.id); fetchFeeds() }} className="rounded-lg p-2 text-text-muted hover:text-warning hover:bg-bg-hover" title="切换状态">
                  <ToggleLeft className="h-4 w-4" />
                </button>
                <button onClick={async () => { await deleteFeed(feed.id); fetchFeeds() }} className="rounded-lg p-2 text-text-muted hover:text-danger hover:bg-bg-hover" title="删除">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
