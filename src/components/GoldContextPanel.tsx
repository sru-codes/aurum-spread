import { useMemo } from 'react'
import { Activity, ExternalLink, Globe2, RefreshCw, ShieldCheck, TrendingUp } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { ContextSnapshot } from '@/lib/data-contracts'
import type { GoldApiLoadState } from '@/hooks/useGoldApi'
import type { GoldApiBar, GoldApiSnapshot } from '@/lib/gold-api'
import { formatIndianCurrency } from '@/lib/analytics'
import './GoldContextPanel.css'

function localDate(value: string | null | undefined) {
  if (!value) return 'Not available'
  const date = new Date(value)
  if (!Number.isFinite(date.valueOf())) return 'Not available'
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: value.includes('T') ? 'short' : undefined, timeZone: 'Asia/Kolkata' }).format(date)
}

function currency(value: string | number | null | undefined, prefix = '') {
  const number = Number(value)
  return Number.isFinite(number) ? `${prefix}${number.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Unavailable'
}

function BarHistory({ bars }: { bars: GoldApiBar[] }) {
  const chart = useMemo(() => {
    const values = bars.map((bar) => Number(bar.close_usd_per_troy_ounce)).filter(Number.isFinite)
    if (!values.length) return null
    const width = 900
    const height = 230
    const pad = { left: 54, right: 18, top: 18, bottom: 34 }
    const min = Math.min(...values)
    const max = Math.max(...values)
    const padding = Math.max((max - min) * 0.15, max * 0.002)
    const floor = min - padding
    const ceiling = max + padding
    const x = (index: number) => pad.left + (index / Math.max(1, values.length - 1)) * (width - pad.left - pad.right)
    const y = (value: number) => pad.top + ((ceiling - value) / (ceiling - floor)) * (height - pad.top - pad.bottom)
    const line = values.map((value, index) => `${index ? 'L' : 'M'} ${x(index).toFixed(2)} ${y(value).toFixed(2)}`).join(' ')
    const area = `${line} L ${x(values.length - 1).toFixed(2)} ${height - pad.bottom} L ${x(0).toFixed(2)} ${height - pad.bottom} Z`
    const dateIndices = [...new Set([0, Math.floor((bars.length - 1) / 2), bars.length - 1])]
    return { width, height, pad, values, x, y, line, area, dateIndices }
  }, [bars])

  if (!chart) return <div className="context-empty">No closed daily bars are available from the selected source.</div>

  return <div className="global-chart-scroll">
    <svg className="global-chart" viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-labelledby="global-chart-title global-chart-desc">
      <title id="global-chart-title">International gold spot daily closing prices</title>
      <desc id="global-chart-desc">Closed XAU/USD reference bars from {bars[0].bar_start_utc.slice(0, 10)} through {bars.at(-1)?.bar_start_utc.slice(0, 10)}, denominated in US dollars per troy ounce.</desc>
      {[0, 0.5, 1].map((fraction) => {
        const value = Math.min(...chart.values) + (Math.max(...chart.values) - Math.min(...chart.values)) * fraction
        const y = chart.y(value)
        return <g key={fraction}><line x1={chart.pad.left} x2={chart.width - chart.pad.right} y1={y} y2={y} className="global-chart-grid" /><text x={chart.pad.left - 9} y={y + 4} textAnchor="end" className="global-chart-axis">{Math.round(value).toLocaleString('en-US')}</text></g>
      })}
      <path d={chart.area} className="global-chart-area" />
      <path d={chart.line} className="global-chart-line" />
      {bars.map((bar, index) => <circle key={bar.bar_start_utc} cx={chart.x(index)} cy={chart.y(Number(bar.close_usd_per_troy_ounce))} r={index === bars.length - 1 ? 4 : 2.2} className="global-chart-point"><title>{bar.bar_start_utc.slice(0, 10)} · close ${currency(bar.close_usd_per_troy_ounce)} per troy ounce</title></circle>)}
      {chart.dateIndices.map((index) => <text key={bars[index].bar_start_utc} x={chart.x(index)} y={chart.height - 9} textAnchor={index === 0 ? 'start' : index === bars.length - 1 ? 'end' : 'middle'} className="global-chart-axis">{bars[index].bar_start_utc.slice(0, 10)}</text>)}
    </svg>
  </div>
}

function Metric({ label, value, note, icon, tone = '' }: { label: string, value: string, note: string, icon: React.ReactNode, tone?: string }) {
  return <Card className={`global-metric ${tone}`}><CardContent>
    <div className="global-metric-label"><span aria-hidden="true">{icon}</span><span>{label}</span></div>
    <strong>{value}</strong><small>{note}</small>
  </CardContent></Card>
}

export default function GoldContextPanel({
  snapshot,
  state,
  error,
  fallback,
  onRefresh,
}: {
  snapshot: GoldApiSnapshot | null
  state: GoldApiLoadState
  error: string | null
  fallback: ContextSnapshot | null
  onRefresh: () => void
}) {
  const gold = snapshot?.sections.gold.data
  const fx = snapshot?.sections.fx.data
  const converted = snapshot?.derived.gold_reference_inr_per_gram
  const fallbackGold = fallback?.international.gold_spot
  const fallbackFx = fallback?.international.usd_inr
  const fallbackConverted = fallback?.international.gold_reference_inr_per_gram
  const goldValue = gold?.price_usd_per_troy_ounce ?? fallbackGold?.price_usd_per_troy_ounce
  const fxValue = fx?.rate ?? fallbackFx?.rate
  const inrGram = converted?.value ?? fallbackConverted?.value
  const bars = snapshot?.sections.bars.data?.bars ?? []
  const sourceProviders = snapshot?.providers ?? []
  const news = [...(snapshot?.sections.news.data?.articles ?? [])].sort((a, b) => Date.parse(b.published_at_utc) - Date.parse(a.published_at_utc))
  const macro = snapshot?.sections.macro.data?.series ?? {}
  const spotUpdated = gold?.computed_at_utc ?? fallbackGold?.computed_at_utc
  const fxEffective = fx?.effective_date ?? fallbackFx?.effective_date
  const snapshotMode = snapshot?.mode ?? (fallback ? 'PARTIAL' : null)
  const isStale = gold?.is_stale ?? fallbackGold?.is_stale ?? false
  const mayBeDelayed = snapshot?.providers.find((provider) => provider.id === 'goldprice.dev')?.authentication?.includes('delayed')
  const isUnavailable = state === 'error' && !snapshot

  return <section className="context-page global-intelligence">
    <div className="page-intro global-intro">
      <div><span className="eyebrow">Supplementary market context</span><h2>Global gold, without confusing it for MCX.</h2><p>International XAU/USD spot and USD/INR help describe the wider market. They do not replace an MCX futures close and do not enter the futures signal calculation.</p></div>
      <div className="global-api-status" aria-live="polite">
        <Badge variant="outline" className={snapshotMode === 'LIVE' ? 'badge-pass' : snapshotMode ? 'badge-watch' : 'badge-neutral'}>{snapshotMode ? `GOLD API · ${snapshotMode}` : state === 'loading' ? 'GOLD API · CONNECTING' : 'GOLD API · UNAVAILABLE'}</Badge>
        <Button size="sm" variant="outline" onClick={onRefresh}><RefreshCw size={14} /> Refresh view</Button>
      </div>
    </div>

    {isUnavailable && <div className="global-inline-message" role="status">Gold API could not be reached{error ? ` · ${error}` : ''}. Showing the last locally published context, if available. This does not affect MCX research.</div>}
    {state === 'ready' && error && <div className="global-inline-message" role="status">Showing the most recent successful Gold API response. The latest refresh failed: {error}</div>}

    <div className="global-metrics">
      <Metric label="International gold spot" value={currency(goldValue, '$')} note={`USD per troy ounce · ${isStale ? 'stale observation' : `${mayBeDelayed ? 'may be delayed · ' : ''}observed ${localDate(spotUpdated)}`}`} icon={<Globe2 size={15} />} tone={isStale ? 'metric-caution' : ''} />
      <Metric label="USD / INR reference" value={fxValue ? Number(fxValue).toFixed(2) : 'Unavailable'} note={fxEffective ? `reference rate effective ${fxEffective}` : 'No exchange-rate observation'} icon={<TrendingUp size={15} />} />
      <Metric label="Converted gold reference" value={inrGram ? formatIndianCurrency(Number(inrGram), 2) : 'Unavailable'} note="INR per gram · contextual, not an MCX settlement" icon={<Activity size={15} />} tone="metric-context" />
    </div>

    <div className="global-content-grid">
      <Card className="global-history-card">
        <CardHeader className="section-heading"><div><div className="heading-line"><CardTitle>International gold history</CardTitle><Badge variant="outline">XAU / USD</Badge></div><p>Closed daily reference bars · USD per troy ounce</p></div><span className="global-history-count">{bars.length} observations</span></CardHeader>
        <CardContent>
          <BarHistory bars={bars} />
          <div className="global-chart-meta"><span>Range {snapshot?.sections.bars.data?.from ?? 'unavailable'} → {snapshot?.sections.bars.data?.to ?? 'unavailable'}</span><span>Source: goldprice.dev via Gold API</span></div>
        </CardContent>
      </Card>

      <Card className="global-breakdown-card">
        <CardHeader className="section-heading"><div><CardTitle>Reference calculation</CardTitle><p>Unit conversion and source timestamps</p></div><ShieldCheck size={16} /></CardHeader>
        <CardContent>
          <code className="global-formula">{converted?.calculation ?? fallbackConverted?.calculation ?? 'XAU/USD ÷ 31.1034768 × USD/INR'}</code>
          <dl className="global-facts">
            <div><dt>Spot observation</dt><dd>{localDate(spotUpdated)}</dd></div>
            <div><dt>FX effective date</dt><dd>{fxEffective ?? 'Not available'}</dd></div>
            <div><dt>Snapshot generated</dt><dd>{localDate(snapshot?.generated_at_utc ?? fallback?.generated_at_utc)}</dd></div>
            <div><dt>Snapshot mode</dt><dd>{snapshotMode ?? 'Unavailable'}</dd></div>
          </dl>
          <p className="global-boundary-note">{converted?.classification ?? fallbackConverted?.classification ?? 'International spot reference; not an exchange settlement, executable quote, or MCX contract price.'}</p>
        </CardContent>
      </Card>
    </div>

    <div className="global-lower-grid">
      <Card className="global-health-card">
        <CardHeader className="section-heading"><div><CardTitle>Provider pulse</CardTitle><p>Health reported by the Gold API service</p></div><span className={`provider-pulse-dot ${snapshotMode?.toLowerCase() ?? 'unknown'}`} aria-hidden="true" /></CardHeader>
        <CardContent>
          {sourceProviders.length ? <div className="provider-pulse-list">{sourceProviders.map((provider) => <div className="provider-pulse-row" key={provider.id}>
            <div><strong>{provider.id}</strong><small>{provider.authentication ?? 'Public read-only context'}</small></div>
            <Badge variant="outline" className={provider.status === 'available' ? 'badge-pass' : provider.status === 'not_configured' ? 'badge-neutral' : 'badge-watch'}>{provider.status.replaceAll('_', ' ')}</Badge>
            <span>{localDate(provider.latest_observation)}</span>
          </div>)}</div> : <div className="context-empty">Provider health is unavailable because the live Gold API snapshot could not be loaded.</div>}
          <div className="global-health-foot">Snapshot refresh cadence: {snapshot ? `${snapshot.refresh_interval_seconds}s` : 'not available'} · Last snapshot: {localDate(snapshot?.generated_at_utc ?? fallback?.generated_at_utc)}</div>
        </CardContent>
      </Card>

      <Card className="global-events-card">
        <CardHeader className="section-heading"><div><CardTitle>Market context</CardTitle><p>Optional dated sources · never signal inputs</p></div></CardHeader>
        <CardContent>
          {news.length ? <div className="context-news-list">{news.slice(0, 3).map((article) => <a key={`${article.url}-${article.published_at_utc}`} href={article.url} target="_blank" rel="noreferrer"><span>{article.source} · {localDate(article.published_at_utc)}</span><strong>{article.title}</strong>{article.description && <small>{article.description}</small>}<ExternalLink size={13} aria-hidden="true" /></a>)}</div> : <p className="context-empty">No news headlines are configured or available. No headline has been generated for this panel.</p>}
          {Object.entries(macro).filter(([, series]) => series.length).map(([id, series]) => {
            const latest = series.at(-1)
            return <div className="macro-context-row" key={id}><span>FRED · {id}</span><strong>{latest?.value ?? 'No value'}</strong><small>{latest?.date ?? 'No observation date'}</small></div>
          })}
          <p className="global-context-foot">News and macro values are dated background only. They are not used to form historical spread signals.</p>
        </CardContent>
      </Card>
    </div>

    <p className="attribution-credit">International gold reference by <a href="https://goldprice.dev" target="_blank" rel="noreferrer">goldprice.dev</a>, delivered by <a href="https://github.com/sru-codes/gold-api" target="_blank" rel="noreferrer">Gold API</a>. Currency reference by <a href="https://frankfurter.dev" target="_blank" rel="noreferrer">Frankfurter</a>. API observation: {localDate(snapshot?.sections.gold.fetched_at_utc)}.</p>
  </section>
}
