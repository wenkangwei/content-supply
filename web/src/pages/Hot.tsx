import { useEffect, useState } from 'react'
import { Zap } from 'lucide-react'
import { getHotKeywords, triggerHotCollection } from '@/api/hot'
import type { HotKeyword, HotPlatform } from '@/api/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { PLATFORM_LABELS } from '@/utils/constants'

export function Hot() {
  const [keywords, setKeywords] = useState<HotKeyword[]>([])
  const [loading, setLoading] = useState(true)
  const [platform, setPlatform] = useState<HotPlatform | ''>('')
  const [triggering, setTriggering] = useState(false)

  const fetchKeywords = async () => {
    setLoading(true)
    try {
      const data = await getHotKeywords({ limit: 50, platform: platform || undefined })
      setKeywords(data)
    } catch { setKeywords([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchKeywords() }, [platform])

  const handleTrigger = async () => {
    setTriggering(true)
    try { await triggerHotCollection() } finally { setTriggering(false) }
    fetchKeywords()
  }

  const platformColor = (p: string) => {
    const colors: Record<string, string> = { hackernews: 'text-orange-400', reddit: 'text-orange-500', google: 'text-blue-400', baidu: 'text-blue-500', weibo: 'text-red-400', zhihu: 'text-blue-300', douyin: 'text-pink-400', twitter: 'text-sky-400' }
    return colors[p] || 'text-text-secondary'
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary">热搜监控</h1>
        <Button size="sm" onClick={handleTrigger} disabled={triggering}>
          <Zap className="h-3.5 w-3.5" /> 触发采集
        </Button>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        <button
          onClick={() => setPlatform('')}
          className={`rounded-lg px-4 py-1.5 text-xs transition-colors ${!platform ? 'bg-accent text-white' : 'bg-bg-secondary text-text-secondary hover:bg-bg-hover'}`}
        >
          全部
        </button>
        {Object.entries(PLATFORM_LABELS).map(([k, v]) => (
          <button
            key={k}
            onClick={() => setPlatform(k as HotPlatform)}
            className={`rounded-lg px-4 py-1.5 text-xs transition-colors ${platform === k ? 'bg-accent text-white' : 'bg-bg-secondary text-text-secondary hover:bg-bg-hover'}`}
          >
            {v}
          </button>
        ))}
      </div>

      {loading ? <Spinner className="py-20" /> : keywords.length === 0 ? <EmptyState message="暂无热搜词" /> : (
        <div className="rounded-xl border border-border bg-bg-secondary px-6">
          {keywords.map((kw, idx) => (
            <div key={kw.id} className={`flex items-center justify-between py-4 ${idx < keywords.length - 1 ? 'border-b border-border/60' : ''}`}>
              <div className="flex items-center gap-4">
                <span className={`flex h-8 w-8 items-center justify-center rounded-full bg-bg-tertiary text-sm font-bold ${platformColor(kw.platform)}`}>
                  {kw.rank}
                </span>
                <div>
                  <span className="text-sm font-medium text-text-primary">{kw.keyword}</span>
                  <div className="mt-0.5 text-xs text-text-muted">
                    <span className={platformColor(kw.platform)}>{PLATFORM_LABELS[kw.platform] || kw.platform}</span>
                    <span className="mx-1.5">·</span>
                    <span>热度 {kw.hot_score.toFixed(0)}</span>
                    {kw.category && <><span className="mx-1.5">·</span><span>{kw.category}</span></>}
                  </div>
                </div>
              </div>
              <Badge variant={kw.content_fetched ? 'success' : 'default'}>
                {kw.content_fetched ? '已抓取' : '未抓取'}
              </Badge>
            </div>
          ))}
        </div>
      )}
      <div className="mt-4 text-xs text-text-muted">共 {keywords.length} 条热搜词</div>
    </div>
  )
}
