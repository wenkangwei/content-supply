import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, SlidersHorizontal } from 'lucide-react'
import { getItems, searchItems, updateItemStatus, getItemCount } from '@/api/items'
import type { Item, ItemSourceType } from '@/api/types'
import { ContentCard } from '@/components/shared/ContentCard'
import { Pagination } from '@/components/ui/Pagination'
import { Spinner } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { PAGE_SIZE, SOURCE_TYPE_LABELS } from '@/utils/constants'

export function Items() {
  const navigate = useNavigate()
  const [items, setItems] = useState<Item[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterSource, setFilterSource] = useState<ItemSourceType | ''>('')

  const fetchItems = useCallback(async () => {
    setLoading(true)
    try {
      let data: Item[]
      if (searchQuery) {
        data = await searchItems({ query: searchQuery, page, page_size: PAGE_SIZE, source_type: filterSource || undefined })
      } else {
        const skip = (page - 1) * PAGE_SIZE
        data = await getItems({ skip, limit: PAGE_SIZE, source_type: filterSource || undefined, status: 'published' })
      }
      setItems(data)
      const countRes = await getItemCount({ status: 'published', source_type: filterSource || undefined })
      setTotal(countRes.total)
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [page, searchQuery, filterSource])

  useEffect(() => { fetchItems() }, [fetchItems])

  const handleArchive = async (id: string) => {
    await updateItemStatus(id, 'archived')
    fetchItems()
  }

  const handleRewrite = async (id: string) => {
    navigate(`/items/${id}`)
  }

  return (
    <div className="mx-auto max-w-3xl">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary">内容池</h1>
        <span className="text-sm text-text-muted">共 {total} 条</span>
      </div>

      {/* Search & Filter */}
      <div className="mb-6 flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1) }}
            placeholder="搜索标题、摘要、内容..."
            className="h-11 w-full rounded-xl border border-border bg-bg-secondary pl-11 pr-4 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none transition-colors"
          />
        </div>
        <div className="relative">
          <SlidersHorizontal className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted pointer-events-none" />
          <select
            value={filterSource}
            onChange={(e) => { setFilterSource(e.target.value as ItemSourceType | ''); setPage(1) }}
            className="h-11 appearance-none rounded-xl border border-border bg-bg-secondary pl-10 pr-8 text-sm text-text-primary focus:border-accent focus:outline-none transition-colors"
          >
            <option value="">全部来源</option>
            {Object.entries(SOURCE_TYPE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Content Feed */}
      {loading ? (
        <Spinner className="py-20" />
      ) : items.length === 0 ? (
        <EmptyState message="暂无内容" />
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <ContentCard
              key={item.id}
              item={item}
              onArchive={handleArchive}
              onRewrite={handleRewrite}
              onClick={() => navigate(`/items/${item.id}`)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="mt-6">
          <Pagination page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
        </div>
      )}
    </div>
  )
}
