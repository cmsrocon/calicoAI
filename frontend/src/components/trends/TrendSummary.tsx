import type { Trend } from '../../types'
import TagChip from '../shared/TagChip'

export default function TrendSummary({ trend }: { trend: Trend }) {
  const sentiment = trend.sentiment_score
  const sentimentLabel = sentiment == null ? null
    : sentiment > 0.3 ? 'Positive'
    : sentiment < -0.3 ? 'Negative'
    : 'Mixed'
  const sentimentColor = sentiment == null ? ''
    : sentiment > 0.3 ? 'text-emerald-400'
    : sentiment < -0.3 ? 'text-red-400'
    : 'text-yellow-400'

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        {sentimentLabel && (
          <span className={`text-xs font-semibold ${sentimentColor}`}>Sentiment: {sentimentLabel}</span>
        )}
        <span className="text-xs text-stone-500">{trend.item_count} items · {new Date(trend.period_start).toLocaleDateString()} – {new Date(trend.period_end).toLocaleDateString()}</span>
      </div>
      {trend.top_themes.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {trend.top_themes.map((theme, i) => (
            <TagChip key={i} label={theme} color="green" />
          ))}
        </div>
      )}
      {trend.narrative && (
        <p className="text-sm text-stone-300 leading-relaxed whitespace-pre-line">{trend.narrative}</p>
      )}
    </div>
  )
}
