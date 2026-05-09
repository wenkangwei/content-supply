import { useEffect, useState } from 'react'
import { Trash2, Check, X } from 'lucide-react'
import { getCleanupPolicies, getPendingCleanups, triggerCleanupScan, confirmCleanup, rejectCleanup } from '@/api/cleanup'
import type { CleanupLog } from '@/api/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'

export function Cleanup() {
  const [policies, setPolicies] = useState<Array<{ source_type: string; ttl_days: number; max_items: number; min_quality: number }>>([])
  const [pending, setPending] = useState<CleanupLog[]>([])
  const [loading, setLoading] = useState(true)
  const [reviewer] = useState('admin')

  const fetchData = async () => {
    setLoading(true)
    try {
      const [p, pend] = await Promise.all([getCleanupPolicies(), getPendingCleanups()])
      setPolicies(p)
      setPending(pend)
    } catch { /* handled */ }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  const handleTrigger = async () => {
    await triggerCleanupScan()
    fetchData()
  }

  const handleConfirm = async (logId: number) => {
    await confirmCleanup(logId, { reviewer })
    fetchData()
  }

  const handleReject = async (logId: number) => {
    await rejectCleanup(logId, { reviewer })
    fetchData()
  }

  const statusVariant = (s: string) => {
    const map: Record<string, 'success' | 'warning' | 'danger' | 'default' | 'info'> = {
      pending_review: 'warning', approved: 'info', executing: 'info', done: 'success', rejected: 'danger', expired: 'default',
    }
    return map[s] || 'default'
  }

  if (loading) return <Spinner className="py-20" />

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary">清理管理</h1>
        <Button size="sm" onClick={handleTrigger}><Trash2 className="h-3.5 w-3.5" /> 触发扫描</Button>
      </div>

      {policies.length > 0 && (
        <div className="mb-6 rounded-xl border border-border bg-bg-secondary p-5">
          <h2 className="mb-4 text-sm font-medium text-text-primary">清理策略</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-text-muted">
                  <th className="pb-3 text-left font-medium">来源</th>
                  <th className="pb-3 text-left font-medium">TTL(天)</th>
                  <th className="pb-3 text-left font-medium">最大条数</th>
                  <th className="pb-3 text-left font-medium">最低质量</th>
                </tr>
              </thead>
              <tbody>
                {policies.map((p, i) => (
                  <tr key={i} className="border-b border-border/50 last:border-b-0">
                    <td className="py-3 text-text-primary">{p.source_type}</td>
                    <td className="py-3">{p.ttl_days}</td>
                    <td className="py-3">{p.max_items}</td>
                    <td className="py-3">{p.min_quality}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {pending.length > 0 && (
        <div className="rounded-xl border border-border bg-bg-secondary p-5">
          <h2 className="mb-4 text-sm font-medium text-text-primary">待审核 ({pending.length})</h2>
          <div className="space-y-3">
            {pending.map((log) => (
              <div key={log.id} className="flex items-center justify-between rounded-lg bg-bg-tertiary p-4">
                <div>
                  <div className="flex items-center gap-2 text-sm text-text-primary">
                    <Badge variant={statusVariant(log.status)}>{log.status}</Badge>
                    <span>{log.policy} · {log.source_type}</span>
                  </div>
                  <div className="mt-1 text-xs text-text-muted">
                    扫描 {log.items_scanned} 条 · 待删 {log.items_to_delete} 条
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button variant="secondary" size="sm" onClick={() => handleConfirm(log.id)}><Check className="h-3 w-3" /> 确认</Button>
                  <Button variant="ghost" size="sm" onClick={() => handleReject(log.id)}><X className="h-3 w-3" /> 拒绝</Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
