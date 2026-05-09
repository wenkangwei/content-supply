import { useState } from 'react'
import { Globe, Send } from 'lucide-react'
import { crawlUrl } from '@/api/crawl'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'

export function Crawl() {
  const [url, setUrl] = useState('')
  const [category, setCategory] = useState('')
  const [result, setResult] = useState<Awaited<ReturnType<typeof crawlUrl>> | null>(null)
  const [loading, setLoading] = useState(false)

  const handleCrawl = async () => {
    if (!url) return
    setLoading(true)
    setResult(null)
    try {
      const data = await crawlUrl({ url, category: category || undefined })
      setResult(data)
    } catch {
      // error handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-6 text-2xl font-bold text-text-primary">爬取中心</h1>

      <div className="mb-6 rounded-xl border border-border bg-bg-secondary p-5">
        <h2 className="mb-3 text-sm font-medium text-text-primary">手动爬取 URL</h2>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Globe className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="输入 URL (支持通用网页、微信公众号文章)"
              className="h-11 w-full rounded-xl border border-border bg-bg-primary pl-9 pr-3 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none"
            />
          </div>
          <input
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="分类 (可选)"
            className="h-11 w-32 rounded-xl border border-border bg-bg-primary px-3 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          <Button onClick={handleCrawl} disabled={!url || loading}>
            <Send className="h-3.5 w-3.5" /> 爬取
          </Button>
        </div>
      </div>

      {loading && <Spinner className="py-10" />}

      {result && (
        <div className="rounded-xl border border-border bg-bg-secondary p-5">
          <h3 className="mb-2 text-sm font-medium text-text-primary">爬取结果</h3>
          <div className="mb-2 text-xs text-text-muted">
            状态: <span className={result.task.status === 'done' ? 'text-success' : 'text-danger'}>{result.task.status}</span>
            {' · '}发现 {result.task.items_found} 条 · 新增 {result.task.items_new} 条
          </div>
          {result.item && (
            <div className="rounded-lg bg-bg-tertiary p-4">
              <p className="text-sm font-medium text-text-primary">{result.item.title}</p>
              <p className="mt-1 text-xs text-text-muted">{result.item.url}</p>
              {result.item.author && <p className="text-xs text-text-muted">作者: {result.item.author}</p>}
            </div>
          )}
          {result.task.error_message && (
            <p className="mt-2 text-xs text-danger">{result.task.error_message}</p>
          )}
        </div>
      )}
    </div>
  )
}
