import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, ExternalLink, PenLine, Archive } from 'lucide-react'
import { getItem, updateItemStatus } from '@/api/items'
import { rewriteItem } from '@/api/rewrite'
import type { Item } from '@/api/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { SOURCE_TYPE_LABELS } from '@/utils/constants'
import { formatDate, decodeHtmlEntities } from '@/utils/format'

function parseTags(tags: string): string[] {
  try {
    const parsed = JSON.parse(tags)
    if (Array.isArray(parsed)) return parsed.filter((t: unknown) => typeof t === 'string')
  } catch { /* not JSON */ }
  return tags.split(',').map((t) => t.trim()).filter(Boolean)
}

export function ItemDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [item, setItem] = useState<Item | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    getItem(id).then(setItem).catch(() => setItem(null)).finally(() => setLoading(false))
  }, [id])

  if (loading) return <Spinner className="py-20" />
  if (!item) return <div className="py-20 text-center text-text-muted">内容不存在</div>

  const handleRewrite = async () => {
    if (!id) return
    await rewriteItem(id, 'paraphrase')
    const updated = await getItem(id)
    setItem(updated)
  }

  const handleArchive = async () => {
    if (!id) return
    await updateItemStatus(id, 'archived')
    navigate('/items')
  }

  const decodedTitle = decodeHtmlEntities(item.title)
  const decodedSummary = item.summary ? decodeHtmlEntities(item.summary) : ''
  const decodedContent = item.content ? decodeHtmlEntities(item.content) : ''
  const decodedOriginal = item.original_content ? decodeHtmlEntities(item.original_content) : ''

  return (
    <div className="mx-auto max-w-3xl">
      <button onClick={() => navigate('/items')} className="mb-6 flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors">
        <ArrowLeft className="h-4 w-4" /> 返回列表
      </button>

      <article className="rounded-xl border border-border bg-bg-secondary p-6">
        {/* Meta */}
        <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-text-muted">
          <span className="rounded-md bg-accent/10 px-2 py-0.5 text-accent">
            {SOURCE_TYPE_LABELS[item.source_type] || item.source_type}
          </span>
          {item.source_name && <span>{item.source_name}</span>}
          <span>{formatDate(item.published_at || item.created_at)}</span>
          {item.author && <span>by {item.author}</span>}
          <span className={item.quality_score >= 0.7 ? 'text-success' : 'text-warning'}>
            质量: {item.quality_score.toFixed(2)}
          </span>
        </div>

        {/* Title + Actions */}
        <div className="mb-4 flex items-start justify-between gap-4">
          <h1 className="text-xl font-bold leading-snug text-text-primary">{decodedTitle}</h1>
          <div className="flex shrink-0 gap-2">
            <Button variant="secondary" size="sm" onClick={handleRewrite}>
              <PenLine className="h-3.5 w-3.5" /> 改写
            </Button>
            <Button variant="ghost" size="sm" onClick={handleArchive}>
              <Archive className="h-3.5 w-3.5" /> 归档
            </Button>
            <a href={item.url} target="_blank" rel="noopener noreferrer">
              <Button variant="secondary" size="sm">
                <ExternalLink className="h-3.5 w-3.5" /> 原文
              </Button>
            </a>
          </div>
        </div>

        {/* Tags */}
        {item.tags && (
          <div className="mb-4 flex flex-wrap gap-1.5">
            {parseTags(item.tags).map((tag) => (
              <Badge key={tag} variant="info">{tag}</Badge>
            ))}
          </div>
        )}

        {/* Hero Image */}
        {item.image_url && (
          <img
            src={item.image_url}
            alt={decodedTitle}
            className="mb-5 w-full rounded-xl object-cover max-h-80"
            loading="lazy"
          />
        )}

        {/* Summary */}
        {decodedSummary && (
          <div className="mb-5 rounded-lg bg-bg-tertiary p-4">
            <p className="text-sm leading-relaxed text-text-secondary">{decodedSummary}</p>
          </div>
        )}

        {/* Content */}
        <div className="prose prose-invert max-w-none">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary">
            {decodedContent || '暂无正文内容'}
          </p>
        </div>

        {/* Original content */}
        {item.is_rewritten && decodedOriginal && (
          <details className="mt-6 border-t border-border pt-4">
            <summary className="cursor-pointer text-sm text-text-muted hover:text-text-primary transition-colors">查看原文</summary>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-text-muted">{decodedOriginal}</p>
          </details>
        )}
      </article>
    </div>
  )
}
