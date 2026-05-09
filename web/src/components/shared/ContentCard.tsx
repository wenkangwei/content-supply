import { ExternalLink, Archive, PenLine } from 'lucide-react'
import type { Item } from '@/api/types'
import { formatDate, decodeHtmlEntities } from '@/utils/format'
import { SOURCE_TYPE_LABELS } from '@/utils/constants'
import { memo } from 'react'

function parseTags(tags: string): string[] {
  try {
    const parsed = JSON.parse(tags)
    if (Array.isArray(parsed)) return parsed.filter((t: unknown) => typeof t === 'string')
  } catch { /* not JSON */ }
  return tags.split(',').map((t) => t.trim()).filter(Boolean)
}

interface Props {
  item: Item
  onRewrite?: (id: string) => void
  onArchive?: (id: string) => void
  onClick?: () => void
}

export const ContentCard = memo(function ContentCard({ item, onRewrite, onArchive, onClick }: Props) {
  const decodedSummary = item.summary ? decodeHtmlEntities(item.summary) : ''
  const decodedTitle = decodeHtmlEntities(item.title)

  return (
    <article
      onClick={onClick}
      className="group cursor-pointer rounded-2xl border border-border-subtle p-4 transition-colors hover:bg-bg-hover"
    >
      {/* Card header: source · author · score */}
      <div className="mb-2 flex items-center gap-2">
        <div className="flex items-center gap-2 text-[11px] text-text-muted">
          <span className="font-mono-accent rounded bg-border-subtle px-2 py-0.5 text-text-secondary">
            {SOURCE_TYPE_LABELS[item.source_type] || item.source_type}
          </span>
          {item.source_name && <span>{item.source_name}</span>}
          {item.author && <span className="text-text-secondary">{item.author}</span>}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="font-mono-accent pill bg-border-subtle font-semibold text-text-muted">
            {item.quality_score.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Title */}
      <h3 className="mb-1.5 text-[15px] font-bold leading-snug text-text-primary group-hover:text-accent transition-colors">
        <a href={item.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
          {decodedTitle}
        </a>
      </h3>

      {/* Summary */}
      {decodedSummary && (
        <p className="mb-2 line-clamp-2 text-[12.5px] leading-5 text-text-secondary">
          {decodedSummary}
        </p>
      )}

      {/* Image */}
      {item.image_url && (
        <div className="mb-3 overflow-hidden rounded-2xl border border-border-subtle">
          <img
            src={item.image_url}
            alt={decodedTitle}
            className="max-h-72 w-full object-cover transition-transform duration-300 group-hover:scale-[1.01]"
            loading="lazy"
            onError={(e) => { (e.currentTarget.style.display = 'none') }}
          />
        </div>
      )}

      {/* Tags */}
      {item.tags && parseTags(item.tags).length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {parseTags(item.tags).slice(0, 5).map((tag) => (
            <span key={tag} className="font-mono-accent pill bg-[rgba(255,255,255,0.08)] text-text-secondary">
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Bottom row: time + actions */}
      <div className="flex items-center justify-between">
        <span className="font-mono-accent text-[11px] text-text-muted">
          {formatDate(item.published_at || item.created_at)}
        </span>
        <div className="flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            onClick={(e) => { e.stopPropagation(); onRewrite?.(item.id) }}
            className="rounded-lg p-1.5 text-text-muted hover:bg-bg-tertiary hover:text-accent"
            title="改写"
          >
            <PenLine className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onArchive?.(item.id) }}
            className="rounded-lg p-1.5 text-text-muted hover:bg-bg-tertiary hover:text-warning"
            title="归档"
          >
            <Archive className="h-3.5 w-3.5" />
          </button>
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="rounded-lg p-1.5 text-text-muted hover:bg-bg-tertiary hover:text-text-primary"
            title="查看原文"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>
    </article>
  )
})
