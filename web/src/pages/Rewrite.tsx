import { useState } from 'react'
import { PenLine, Play } from 'lucide-react'
import { batchRewrite } from '@/api/rewrite'
import type { ItemSourceType, RewriteType } from '@/api/types'
import { Button } from '@/components/ui/Button'
import { REWRITE_TYPE_LABELS, SOURCE_TYPE_LABELS } from '@/utils/constants'

export function Rewrite() {
  const [rewriteType, setRewriteType] = useState<RewriteType>('paraphrase')
  const [sourceType, setSourceType] = useState<ItemSourceType | ''>('')
  const [limit, setLimit] = useState(10)
  const [result, setResult] = useState<string>('')
  const [loading, setLoading] = useState(false)

  const handleBatch = async () => {
    setLoading(true)
    setResult('')
    try {
      const res = await batchRewrite({ rewrite_type: rewriteType, source_type: sourceType || undefined, limit })
      setResult(`已创建 ${res.tasks_created} 个改写任务`)
    } catch {
      setResult('改写任务创建失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-6 text-2xl font-bold text-text-primary">内容改写</h1>

      <div className="rounded-xl border border-border bg-bg-secondary p-6">
        <h2 className="mb-4 text-sm font-medium text-text-primary">批量改写</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs text-text-muted">改写模式</label>
            <select value={rewriteType} onChange={(e) => setRewriteType(e.target.value as RewriteType)} className="h-10 w-full rounded-lg border border-border bg-bg-primary px-3 text-sm text-text-primary focus:border-accent focus:outline-none">
              {Object.entries(REWRITE_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-text-muted">来源类型</label>
            <select value={sourceType} onChange={(e) => setSourceType(e.target.value as ItemSourceType | '')} className="h-10 w-full rounded-lg border border-border bg-bg-primary px-3 text-sm text-text-primary focus:border-accent focus:outline-none">
              <option value="">全部来源</option>
              {Object.entries(SOURCE_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-text-muted">处理条数</label>
            <input type="number" value={limit} onChange={(e) => setLimit(Number(e.target.value))} min={1} max={100} className="h-10 w-full rounded-lg border border-border bg-bg-primary px-3 text-sm text-text-primary focus:border-accent focus:outline-none" />
          </div>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={handleBatch} disabled={loading}>
            <Play className="h-3.5 w-3.5" /> 开始批量改写
          </Button>
          {result && <span className="text-sm text-text-secondary">{result}</span>}
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-border bg-bg-secondary p-5">
        <h3 className="mb-3 text-sm font-medium text-text-primary">改写模式说明</h3>
        <div className="space-y-2 text-xs text-text-secondary">
          <div><PenLine className="mr-2 inline h-3 w-3 text-accent" /><strong>伪原创</strong>: 保持内容主旨，改写表达方式，规避版权风险</div>
          <div><PenLine className="mr-2 inline h-3 w-3 text-warning" /><strong>摘要</strong>: 长文精简，提取核心信息</div>
          <div><PenLine className="mr-2 inline h-3 w-3 text-success" /><strong>扩展</strong>: 短文扩充，增加信息量和细节</div>
        </div>
      </div>
    </div>
  )
}
