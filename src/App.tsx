import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity, AlertTriangle, CalendarClock, CheckCircle2,
  CircleHelp, Code2, Database, Download, FileUp, Globe2, Info, Moon, RefreshCw,
  ShieldCheck, Sun, TrendingUp, XCircle,
} from 'lucide-react'
import FadeContent from '@/components/FadeContent'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import {
  bundleFromSnapshot, parseContextSnapshot, parseResearchBundle, parseResearchSnapshot,
  type ContextSnapshot, type DataMode, type ResearchBundle, type ResearchPointJson,
  type ResearchSnapshot,
} from '@/lib/data-contracts'
import { formatIndianCurrency, formatNumber } from '@/lib/analytics'
import './App.css'

type LoadState = 'loading' | 'ready' | 'error'

function shortDate(value: string) {
  return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short' }).format(new Date(`${value.slice(0, 10)}T00:00:00Z`))
}

function dateTime(value: string | null | undefined) {
  if (!value) return 'Not available'
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: value.includes('T') ? 'short' : undefined, timeZone: 'Asia/Kolkata' }).format(new Date(value.includes('T') ? value : `${value}T00:00:00Z`))
}

function signed(value: number, digits = 1) {
  return `${value > 0 ? '+' : ''}${value.toFixed(digits)}`
}

function MetricCard({ label, value, detail, tone = 'default', icon }: {
  label: string
  value: string
  detail: string
  tone?: 'default' | 'positive' | 'warning' | 'negative'
  icon: React.ReactNode
}) {
  return <Card className={`metric-card tone-${tone}`}>
    <CardHeader><span className="metric-icon" aria-hidden="true">{icon}</span><span className="eyebrow">{label}</span></CardHeader>
    <CardContent><strong>{value}</strong><span>{detail}</span></CardContent>
  </Card>
}

function SpreadChart({ points, pair }: { points: ResearchPointJson[], pair: string }) {
  const width = 920
  const height = 300
  const pad = { left: 54, right: 18, top: 22, bottom: 38 }
  const chartWidth = width - pad.left - pad.right
  const chartHeight = height - pad.top - pad.bottom
  const allValues = points.flatMap((point) => {
    const band = point.trailing_mean_bps !== null && point.trailing_stdev_bps !== null
      ? [point.trailing_mean_bps - 2 * point.trailing_stdev_bps, point.trailing_mean_bps + 2 * point.trailing_stdev_bps]
      : []
    return [point.residual_spread_bps, ...band]
  })
  const bound = Math.max(5, Math.ceil(Math.max(...allValues.map(Math.abs)) / 5) * 5)
  const x = (index: number) => pad.left + (index / Math.max(1, points.length - 1)) * chartWidth
  const y = (value: number) => pad.top + ((bound - value) / (bound * 2)) * chartHeight
  const pathFor = (getter: (point: ResearchPointJson) => number | null) => {
    let drawing = false
    return points.map((point, index) => {
      const value = getter(point)
      if (value === null) { drawing = false; return '' }
      const command = drawing ? 'L' : 'M'
      drawing = true
      return `${command} ${x(index).toFixed(1)} ${y(value).toFixed(1)}`
    }).join(' ')
  }
  const spreadPath = pathFor((point) => point.residual_spread_bps)
  const upperPath = pathFor((point) => point.trailing_mean_bps === null || point.trailing_stdev_bps === null ? null : point.trailing_mean_bps + 2 * point.trailing_stdev_bps)
  const lowerPath = pathFor((point) => point.trailing_mean_bps === null || point.trailing_stdev_bps === null ? null : point.trailing_mean_bps - 2 * point.trailing_stdev_bps)
  const ticks = [-bound, -bound / 2, 0, bound / 2, bound]
  const labelIndexes = [...new Set([0, Math.floor((points.length - 1) / 3), Math.floor((points.length - 1) * 2 / 3), points.length - 1])]
  return <div className="chart-wrap">
    <svg className="spread-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby="spread-title spread-desc">
      <title id="spread-title">{pair} carry-adjusted residual spread</title>
      <desc id="spread-desc">Past-only statistical bands and residual spread in basis points. Data points expose exact values as SVG titles.</desc>
      {ticks.map((tick) => <g key={tick}>
        <line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} className={tick === 0 ? 'chart-zero' : 'chart-grid'} />
        <text x={pad.left - 10} y={y(tick) + 4} textAnchor="end" className="chart-axis">{tick.toFixed(0)}</text>
      </g>)}
      <path d={upperPath} className="chart-band" />
      <path d={lowerPath} className="chart-band" />
      <path d={spreadPath} className="chart-line" />
      {points.map((point, index) => <circle key={point.trading_date} cx={x(index)} cy={y(point.residual_spread_bps)} r={index === points.length - 1 ? 4.5 : 2} className="chart-point">
        <title>{point.trading_date}: {point.residual_spread_bps.toFixed(2)} bps · z {point.zscore?.toFixed(2) ?? 'unavailable'}</title>
      </circle>)}
      {labelIndexes.map((index) => <text key={index} x={x(index)} y={height - 9} textAnchor="middle" className="chart-axis">{shortDate(points[index].trading_date)}</text>)}
      <text x={7} y={15} className="chart-unit">basis points</text>
    </svg>
  </div>
}

function ModeBadge({ mode }: { mode: DataMode }) {
  return <Badge variant="outline" className={mode === 'DEMO' ? 'badge-demo' : 'badge-verified'}>{mode === 'DEMO' ? 'DEMO · SYNTHETIC' : 'VERIFIED HISTORICAL'}</Badge>
}

function ResearchTerminal({ bundle, onDownload }: { bundle: ResearchBundle, onDownload: (snapshot: ResearchSnapshot) => void }) {
  const pairs = useMemo(() => Object.keys(bundle.analyses), [bundle])
  const [pair, setPair] = useState(pairs[0])
  const windows = useMemo(() => Object.keys(bundle.analyses[pair] ?? {}).sort((a, b) => Number(a) - Number(b)), [bundle, pair])
  const [lookback, setLookback] = useState(windows.includes('40') ? '40' : windows[0])
  const [range, setRange] = useState('60')
  const [selectedDate, setSelectedDate] = useState('latest')
  const [slippage, setSlippage] = useState('2')

  const changePair = (nextPair: string) => {
    const nextWindows = Object.keys(bundle.analyses[nextPair] ?? {}).sort((a, b) => Number(a) - Number(b))
    setPair(nextPair)
    setLookback(nextWindows.includes('40') ? '40' : nextWindows[0])
    setSelectedDate('latest')
  }

  const snapshot = bundle.analyses[pair]?.[lookback] ?? Object.values(bundle.analyses[pair] ?? {})[0]
  if (!snapshot) return <EmptyState title="No analysis for this selection" copy="Generate a snapshot for the chosen expiries and lookback, then reload it." />
  const fullSeries = snapshot.series
  const shownSeries = range === 'all' ? fullSeries : fullSeries.slice(-Number(range))
  const point = selectedDate === 'latest' ? fullSeries.at(-1)! : fullSeries.find((item) => item.trading_date === selectedDate) ?? fullSeries.at(-1)!
  const failedGates = point.gates.filter((gate) => !gate.passed)
  const testSimulation = snapshot.partition_simulations.test
  const testScenarios = snapshot.partition_cost_sensitivity.test ?? []
  const scenario = testScenarios.find((item) => item.slippage_bps === Number(slippage)) ?? testScenarios[0]
  const totalCosts = testSimulation.brokerage_inr + testSimulation.fees_inr + testSimulation.slippage_inr + testSimulation.funding_inr
  const verdictLabel = point.verdict === 'NO_SIGNAL' ? 'No signal' : point.verdict.replaceAll('_', ' ').toLowerCase()

  return <FadeContent duration={350} threshold={0.02}>
    <div className="mode-strip"><ModeBadge mode={bundle.mode} /><span>{bundle.disclaimer}</span><Button size="sm" variant="outline" onClick={() => onDownload(snapshot)}><Download size={14} /> Export selected run</Button></div>
    <section className="summary-row" aria-label="Selected research state">
      <MetricCard label="Residual spread" value={`${signed(point.residual_spread_bps)} bps`} detail={`Raw ${signed(point.raw_spread_bps)} · carry ${signed(point.expiry_carry_bps)}`} tone="warning" icon={<Activity size={16} />} />
      <MetricCard label="Walk-forward z-score" value={point.zscore === null ? 'Unavailable' : `${point.zscore.toFixed(2)}σ`} detail={`${lookback} prior sessions only`} tone={point.zscore !== null && Math.abs(point.zscore) >= snapshot.configuration.entry_z ? 'warning' : 'default'} icon={<TrendingUp size={16} />} />
      <MetricCard label="Selected test cost scenario" value={scenario ? formatIndianCurrency(scenario.net_pnl_inr, 0) : 'Unavailable'} detail={`${slippage} bps slippage · untouched test partition`} tone={scenario ? scenario.net_pnl_inr >= 0 ? 'positive' : 'negative' : 'default'} icon={<ShieldCheck size={16} />} />
      <MetricCard label="Verdict" value={verdictLabel} detail={failedGates.length ? `${failedGates.length} eligibility gate${failedGates.length === 1 ? '' : 's'} failed` : 'All eligibility gates passed'} tone={point.verdict === 'NO_SIGNAL' ? 'default' : 'positive'} icon={point.verdict === 'NO_SIGNAL' ? <XCircle size={16} /> : <CheckCircle2 size={16} />} />
    </section>

    <section className="analysis-grid">
      <Card className="chart-card">
        <CardHeader className="section-heading chart-heading">
          <div><div className="heading-line"><CardTitle>Expiry-aware spread</CardTitle><ModeBadge mode={bundle.mode} /></div><p>Residual after declared carry · independent engine output for {pair}</p></div>
          <div className="chart-controls">
            <label><span className="control-label">Pair + expiries</span><NativeSelect value={pair} onChange={(event) => changePair(event.target.value)}>{pairs.map((item) => {
              const selected = Object.values(bundle.analyses[item])[0]
              return <NativeSelectOption key={item} value={item}>{item} · {shortDate(selected.pair.candidate_expiry)}/{shortDate(selected.pair.reference_expiry)}</NativeSelectOption>
            })}</NativeSelect></label>
            <div><span className="control-label">Lookback</span><div className="segmented" aria-label="Walk-forward lookback window">{windows.map((value) => <button key={value} type="button" className={lookback === value ? 'active' : ''} onClick={() => { setLookback(value); setSelectedDate('latest') }} aria-pressed={lookback === value}>{value}d</button>)}</div></div>
            <label><span className="control-label">Chart range</span><NativeSelect value={range} onChange={(event) => setRange(event.target.value)}><NativeSelectOption value="30">30 sessions</NativeSelectOption><NativeSelectOption value="60">60 sessions</NativeSelectOption><NativeSelectOption value="all">Full sample</NativeSelectOption></NativeSelect></label>
          </div>
        </CardHeader>
        <CardContent>
          <SpreadChart points={shownSeries} pair={pair} />
          <div className="chart-legend"><span><i className="legend-line" /> carry-adjusted residual</span><span><i className="legend-dash" /> trailing ±2σ</span><span><i className="legend-zero" /> parity</span><span>Source: {bundle.mode === 'DEMO' ? 'engine-generated synthetic fixture' : 'official MCX import'}</span></div>
        </CardContent>
      </Card>

      <Card className="decision-card">
        <CardHeader className="section-heading"><div><span className="eyebrow">Signal autopsy</span><CardTitle>{verdictLabel}</CardTitle></div><span className={`status-light ${point.verdict !== 'NO_SIGNAL' ? 'go' : ''}`} /></CardHeader>
        <CardContent>
          <label className="time-select"><span>Historical time machine</span><NativeSelect value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)}><NativeSelectOption value="latest">Latest · {point.trading_date}</NativeSelectOption>{fullSeries.map((item) => <NativeSelectOption key={item.trading_date} value={item.trading_date}>{item.trading_date} · {item.partition}</NativeSelectOption>)}</NativeSelect></label>
          <div className="trace-formula">
            <span>Calculation trace</span>
            <code>{point.raw_spread_bps.toFixed(2)} raw − {point.expiry_carry_bps.toFixed(2)} carry = {point.residual_spread_bps.toFixed(2)} bps</code>
            <code>({point.residual_spread_bps.toFixed(2)} − {point.trailing_mean_bps?.toFixed(2) ?? 'n/a'}) ÷ {point.trailing_stdev_bps?.toFixed(2) ?? 'n/a'} = {point.zscore?.toFixed(2) ?? 'n/a'}σ</code>
          </div>
          <div className="gate-list">{point.gates.map((gate) => <div key={gate.name} className={gate.passed ? '' : 'blocked'}>{gate.passed ? <CheckCircle2 size={15} /> : <XCircle size={15} />}<span>{gate.name.replaceAll('_', ' ')}</span><strong>{gate.observed}</strong><small>{gate.threshold}</small></div>)}</div>
          <div className="decision-note"><Info size={15} /><p>State: {point.market_state}; liquidity: {point.liquidity_state}; partition: {point.partition}. This decision uses only observations before or on {point.trading_date}; hypothetical execution occurs next session.</p></div>
        </CardContent>
      </Card>
    </section>

    <section className="lower-grid">
      <Card className="contracts-card">
        <CardHeader className="section-heading"><div><CardTitle>Gold futures monitor</CardTitle><p>Explicit expiries · normalized fine-gold values</p></div><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon-sm" aria-label="About normalized prices"><CircleHelp size={16} /></Button></TooltipTrigger><TooltipContent>Close ÷ quoted grams ÷ purity</TooltipContent></Tooltip></CardHeader>
        <CardContent><Table><TableHeader><TableRow><TableHead>Contract</TableHead><TableHead>Expiry</TableHead><TableHead className="numeric">Close</TableHead><TableHead className="numeric">Fine gold ₹/g</TableHead><TableHead className="numeric">Volume</TableHead><TableHead className="numeric">OI</TableHead><TableHead>Status</TableHead></TableRow></TableHeader><TableBody>{bundle.contracts.map((contract) => <TableRow key={`${contract.symbol}-${contract.expiry_date}`}>
          <TableCell><strong>{contract.symbol}</strong><span className="cell-note">{contract.trading_unit_grams || '—'}g lot · {contract.purity ? `${Math.round(contract.purity * 1000)} purity` : 'spec in lineage'}</span></TableCell>
          <TableCell>{shortDate(contract.expiry_date)}<span className="cell-note">{contract.days_to_expiry} calendar days</span></TableCell>
          <TableCell className="numeric mono">{formatIndianCurrency(Number(contract.close), 0)}</TableCell>
          <TableCell className="numeric mono">{formatIndianCurrency(Number(contract.fine_gold_price_per_gram), 2)}</TableCell>
          <TableCell className="numeric mono">{formatNumber(contract.volume_lots)}</TableCell>
          <TableCell className="numeric mono">{formatNumber(contract.open_interest_lots)}</TableCell>
          <TableCell><Badge variant="outline" className={contract.volume_lots >= 10 && contract.days_to_expiry > 7 ? 'badge-pass' : 'badge-watch'}>{contract.volume_lots >= 10 && contract.days_to_expiry > 7 ? 'ELIGIBLE' : 'REVIEW'}</Badge></TableCell>
        </TableRow>)}</TableBody></Table></CardContent>
      </Card>

      <Card className="backtest-card">
          <CardHeader className="section-heading"><div><CardTitle>Attribution laboratory</CardTitle><p>Untouched test partition · actual contract closes and integer lots</p></div><Badge variant="outline">60 / 20 / 20</Badge></CardHeader>
        <CardContent>
          <label className="scenario-control"><span>Hypothetical slippage · test only</span><div className="segmented">{testScenarios.map((item) => <button key={item.slippage_bps} type="button" className={slippage === String(item.slippage_bps) ? 'active' : ''} onClick={() => setSlippage(String(item.slippage_bps))}>{item.slippage_bps} bps</button>)}</div></label>
          <div className="backtest-hero"><span>Net P&amp;L at selected test scenario</span><strong className={scenario && scenario.net_pnl_inr >= 0 ? 'positive' : 'negative'}>{scenario ? formatIndianCurrency(scenario.net_pnl_inr, 0) : 'Unavailable'}</strong><small>{testSimulation.trades} entries · max drawdown {formatIndianCurrency(testSimulation.max_drawdown_inr, 0)}</small></div>
          <div className="attribution"><div><span>Gross contract P&amp;L</span><strong>{formatIndianCurrency(testSimulation.gross_pnl_inr, 0)}</strong></div><div><span>Relative convergence</span><strong>{formatIndianCurrency(testSimulation.relative_convergence_pnl_inr, 0)}</strong></div><div><span>Gold exposure</span><strong>{formatIndianCurrency(testSimulation.gold_exposure_pnl_inr, 0)}</strong></div><div><span>Unexplained residual</span><strong>{formatIndianCurrency(testSimulation.unexplained_residual_pnl_inr, 2)}</strong></div><div><span>Base-run costs</span><strong className="negative">−{formatIndianCurrency(totalCosts, 0)}</strong></div></div>
          <p className="fine-print">Hypothetical next-session close fills plus stated slippage. Bhavcopy volume is activity, not proof of fillable depth. Negative findings remain visible.</p>
        </CardContent>
      </Card>
    </section>
  </FadeContent>
}

function GlobalIntelligence({ context, state, now }: { context: ContextSnapshot | null, state: LoadState, now: number }) {
  if (state === 'loading') return <LoadingState copy="Loading attributed reference-market context…" />
  if (state === 'error' || !context) return <EmptyState title="Reference providers unavailable" copy="MCX research remains usable. Run the Python context refresh when provider access returns." />
  const spot = context.international.gold_spot
  const fx = context.international.usd_inr
  const reference = context.international.gold_reference_inr_per_gram
  const snapshotAgeMs = now - Date.parse(context.generated_at_utc)
  const spotIsStale = Boolean(spot && (spot.is_stale || snapshotAgeMs > 30 * 60_000))
  return <section className="context-page">
    <div className="page-intro"><span className="eyebrow">Supplementary market context</span><h2>Global gold, without confusing it for MCX.</h2><p>XAU/USD spot and USD/INR are reference observations. They can explain a domestic basis, but they are never substituted for a missing futures contract.</p></div>
    <div className="context-metrics">
      <MetricCard label="XAU/USD spot reference" value={spot ? `$${Number(spot.price_usd_per_troy_ounce).toLocaleString('en-US', { maximumFractionDigits: 2 })}` : 'Unavailable'} detail={spot ? `per troy ounce · ${spotIsStale ? 'snapshot stale' : '15-minute delayed free tier'}` : 'No observation'} tone={spotIsStale ? 'warning' : 'default'} icon={<Globe2 size={16} />} />
      <MetricCard label="USD/INR reference" value={fx ? Number(fx.rate).toFixed(2) : 'Unavailable'} detail={fx ? `effective ${fx.effective_date}` : 'No observation'} icon={<TrendingUp size={16} />} />
      <MetricCard label="Converted gold reference" value={reference ? formatIndianCurrency(Number(reference.value), 2) : 'Unavailable'} detail="Per gram · contextual calculation" tone="warning" icon={<Activity size={16} />} />
    </div>
    <Card className="context-detail"><CardHeader className="section-heading"><div><CardTitle>Reference calculation</CardTitle><p>Units and effective dates remain explicit</p></div><Badge variant="outline">SUPPLEMENTARY</Badge></CardHeader><CardContent>
      <code>{reference?.calculation ?? 'Waiting for both XAU/USD and USD/INR'}</code>
      <div className="context-grid"><div><span>Gold timestamp</span><strong>{reference ? dateTime(reference.gold_timestamp_utc) : '—'}</strong></div><div><span>FX effective date</span><strong>{reference?.fx_effective_date ?? '—'}</strong></div><div><span>Context artifact generated</span><strong>{dateTime(context.generated_at_utc)}</strong></div><div><span>Gold source type</span><strong>International spot reference</strong></div><div><span>Domestic source type</span><strong>MCX futures · separate dataset</strong></div></div>
      <p>{reference?.classification}</p>
    </CardContent></Card>
    <p className="attribution-credit">Reference gold data by <a href="https://goldprice.dev" target="_blank" rel="noreferrer">goldprice.dev</a>. FX reference by <a href="https://frankfurter.dev" target="_blank" rel="noreferrer">Frankfurter</a>.</p>
  </section>
}

function SourceCenter({ bundle, context, now }: { bundle: ResearchBundle, context: ContextSnapshot | null, now: number }) {
  const providerRows = (context?.providers ?? []).map((provider) => {
    const refreshed = provider.last_successful_update ? Date.parse(provider.last_successful_update) : NaN
    const staleAfter = provider.id === 'goldprice.dev' ? 30 * 60_000 : 36 * 60 * 60_000
    return provider.status === 'available' && Number.isFinite(refreshed) && now - refreshed > staleAfter
      ? { ...provider, status: 'stale_snapshot' }
      : provider
  })
  const mcx = {
    id: 'MCX Bhavcopy', status: bundle.mode === 'VERIFIED_HISTORICAL' ? 'available' : 'awaiting_import',
    latest_observation: bundle.mode === 'VERIFIED_HISTORICAL' ? bundle.latest_observation_date : null,
    authentication: 'Manual official export · no API key',
    coverage: bundle.mode === 'VERIFIED_HISTORICAL' ? 'Loaded research snapshot' : 'No verified history committed',
    limitations: bundle.mode === 'VERIFIED_HISTORICAL' ? 'Closing values are not guaranteed fills' : 'Automated MCX access blocked; demo data remains synthetic',
  }
  const providers = [mcx, ...providerRows]
  return <section className="source-page"><div className="page-intro"><span className="eyebrow">Quality and provenance</span><h2>Every source declares what it can—and cannot—prove.</h2><p>Provider failures are isolated. Supplementary context can disappear without changing contract research or inventing a replacement.</p></div>
    <Card className="source-table-card"><CardContent><Table><TableHeader><TableRow><TableHead>Provider</TableHead><TableHead>Status</TableHead><TableHead>Latest observation</TableHead><TableHead>Authentication</TableHead><TableHead>Coverage</TableHead><TableHead>Known limitation</TableHead></TableRow></TableHeader><TableBody>{providers.map((provider) => <TableRow key={provider.id}><TableCell><strong>{provider.id}</strong></TableCell><TableCell><Badge variant="outline" className={provider.status === 'available' ? 'badge-pass' : provider.status === 'error' ? 'badge-watch' : 'badge-neutral'}>{provider.status.replaceAll('_', ' ')}</Badge></TableCell><TableCell>{dateTime(provider.latest_observation)}</TableCell><TableCell>{provider.authentication}</TableCell><TableCell>{provider.coverage}</TableCell><TableCell>{provider.limitations}</TableCell></TableRow>)}</TableBody></Table></CardContent></Card>
    <div className="quality-grid"><Card><CardContent><ShieldCheck size={18} /><h3>Research identity</h3><code>{bundle.content_sha256}</code><p>SHA-256 declared by the generated artifact. For verified use, reconcile it with the local manifest and raw archive.</p></CardContent></Card><Card><CardContent><Database size={18} /><h3>Import policy</h3><p>Target futures rows are never silently dropped, duplicate keys abort a merge, and rejected daily imports do not publish clean data.</p></CardContent></Card><Card><CardContent><CalendarClock size={18} /><h3>Refresh model</h3><p>Railway serves static snapshots. Refresh reloads those artifacts; provider jobs run explicitly in Python and never expose API keys to the browser.</p></CardContent></Card></div>
  </section>
}

function Methodology() {
  const steps = [
    ['01', 'Archive', 'Preserve raw official bytes, retrieval time, filename, and SHA-256 before parsing.'],
    ['02', 'Validate', 'Require FUTCOM, exact requested date, consistent OHLC, whole-number activity, and unique date-symbol-expiry identity.'],
    ['03', 'Normalize', 'Convert quoted prices to rupees per gram of fine gold using effective-dated quotation base and purity.'],
    ['04', 'Separate carry', 'Report raw relative spread, declared expiry-carry adjustment, and residual spread independently.'],
    ['05', 'Walk forward', 'Use only prior sessions for every mean, volatility estimate, decision, and model partition.'],
    ['06', 'Attribute', 'Use actual contract closes and integer lots; separate convergence, gold exposure, costs, and unexplained residual.'],
  ]
  return <section className="method-page"><div className="page-intro"><span className="eyebrow">Research design</span><h2>A signal that is allowed to say “nothing today.”</h2><p>Eligibility is evidence, not decoration. A statistically unusual price can still fail liquidity, lifecycle, expiry, market-state, or cost tests.</p></div><div className="method-grid">{steps.map(([number, title, copy]) => <Card key={number} className="method-card"><CardContent><span>{number}</span><h3>{title}</h3><p>{copy}</p></CardContent></Card>)}</div><Card className="formula-card"><CardHeader><CardTitle>Core normalization</CardTitle></CardHeader><CardContent><code>fine_gold_price = close ÷ quoted_grams ÷ purity</code><p>GOLDM is quoted per 10g at 995 purity; GOLDTEN, GOLDGUINEA, and GOLDPETAL use 999 purity with their own quotation bases. Trading-unit size controls lot P&amp;L, not quoted-price normalization.</p></CardContent></Card></section>
}

function LoadingState({ copy }: { copy: string }) {
  return <div className="state-panel" role="status"><RefreshCw className="spin" size={20} /><h2>Loading research artifacts</h2><p>{copy}</p></div>
}

function EmptyState({ title, copy }: { title: string, copy: string }) {
  return <div className="state-panel" role="alert"><AlertTriangle size={20} /><h2>{title}</h2><p>{copy}</p></div>
}

function App() {
  const [bundle, setBundle] = useState<ResearchBundle | null>(null)
  const [context, setContext] = useState<ContextSnapshot | null>(null)
  const [researchState, setResearchState] = useState<LoadState>('loading')
  const [contextState, setContextState] = useState<LoadState>('loading')
  const [message, setMessage] = useState('Loading versioned artifacts…')
  const [now, setNow] = useState(() => Date.now())
  const [dark, setDark] = useState(() => localStorage.getItem('aurum-theme') === 'dark')
  const inputRef = useRef<HTMLInputElement>(null)

  const loadArtifacts = useCallback(async (bustCache = false) => {
    const suffix = bustCache ? `?t=${Date.now()}` : ''
    setResearchState('loading')
    setContextState('loading')
    const [researchResult, contextResult] = await Promise.allSettled([
      fetch(`/data/demo-research.v1.json${suffix}`).then((response) => {
        if (!response.ok) throw new Error(`Research artifact HTTP ${response.status}`)
        return response.json()
      }).then(parseResearchBundle),
      fetch(`/data/context.v1.json${suffix}`).then((response) => {
        if (!response.ok) throw new Error(`Context artifact HTTP ${response.status}`)
        return response.json()
      }).then(parseContextSnapshot),
    ])
    if (researchResult.status === 'fulfilled') {
      setBundle(researchResult.value)
      setResearchState('ready')
    } else {
      setResearchState('error')
    }
    if (contextResult.status === 'fulfilled') {
      setContext(contextResult.value)
      setContextState('ready')
    } else {
      setContextState('error')
    }
    setMessage(`Artifacts checked · ${new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`)
    setNow(Date.now())
  }, [])

  // Artifact loading is the external synchronization this effect owns.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void loadArtifacts() }, [loadArtifacts])
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light'
    localStorage.setItem('aurum-theme', dark ? 'dark' : 'light')
  }, [dark])

  const importSnapshot = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      const parsed: unknown = JSON.parse(await file.text())
      const loaded = typeof parsed === 'object' && parsed !== null && 'analyses' in parsed
        ? parseResearchBundle(parsed)
        : bundleFromSnapshot(parseResearchSnapshot(parsed))
      setBundle(loaded)
      setResearchState('ready')
      setMessage(`${loaded.mode === 'VERIFIED_HISTORICAL' ? 'Verified-mode' : 'Demo'} artifact loaded locally · ${file.name}`)
    } catch (error) {
      setMessage(`Import rejected · ${error instanceof Error ? error.message : 'invalid JSON'}`)
    } finally {
      event.target.value = ''
    }
  }

  const download = (snapshot: ResearchSnapshot) => {
    const filename = `aurum-${snapshot.pair.candidate_symbol.toLowerCase()}-${snapshot.pair.reference_symbol.toLowerCase()}-${snapshot.configuration.lookback_sessions}d-${snapshot.mode.toLowerCase()}.json`
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob([JSON.stringify(snapshot, null, 2)], { type: 'application/json' }))
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
    setMessage(`Research snapshot downloaded · ${filename}`)
  }

  return <TooltipProvider><div className="app-shell">
    <header className="topbar"><div className="brand-block"><div className="brand-mark" aria-hidden="true">Au</div><div><strong>Aurum Spread</strong><span>Commodity derivatives intelligence</span></div></div><div className="header-actions"><div className="data-state"><span className={bundle?.mode === 'VERIFIED_HISTORICAL' ? 'verified-dot' : ''} /><div><strong>{bundle?.mode === 'VERIFIED_HISTORICAL' ? 'Verified historical' : 'Research demo'}</strong><small aria-live="polite">{message}</small></div></div><input ref={inputRef} type="file" accept="application/json,.json" className="sr-only" onChange={importSnapshot} /><Button variant="outline" size="sm" onClick={() => inputRef.current?.click()}><FileUp size={14} /> Import snapshot</Button><Button variant="outline" size="sm" onClick={() => void loadArtifacts(true)}><RefreshCw size={14} /> Refresh artifacts</Button><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon-sm" onClick={() => setDark((value) => !value)} aria-label={`Use ${dark ? 'light' : 'dark'} theme`}>{dark ? <Sun size={16} /> : <Moon size={16} />}</Button></TooltipTrigger><TooltipContent>{dark ? 'Light theme' : 'Dark theme'}</TooltipContent></Tooltip></div></header>
    <main><section className="hero-copy"><div><span className="eyebrow">Hack in Hills ’26 · Problem 03</span><h1>Find the spread.<br /><em>Prove the edge.</em></h1></div><p>A defensible monitor for MCX gold futures—expiry-aware, normalized for fine gold, and evaluated without hindsight. Context is global; evidence stays contract-specific.</p></section>
      <Tabs defaultValue="monitor"><div className="nav-row"><TabsList variant="line" aria-label="Product sections"><TabsTrigger value="monitor">Futures monitor</TabsTrigger><TabsTrigger value="global">Global gold</TabsTrigger><TabsTrigger value="sources">Data sources</TabsTrigger><TabsTrigger value="method">Methodology</TabsTrigger></TabsList><a className="repo-link" href="https://github.com/sru-codes/aurum-spread" target="_blank" rel="noreferrer"><Code2 size={15} /> Repository</a></div>
        <TabsContent value="monitor">{researchState === 'loading' ? <LoadingState copy="Loading the deterministic engine output…" /> : researchState === 'error' || !bundle ? <EmptyState title="Research artifact unavailable" copy="Run analytics/generate_demo.py or import a generated verified snapshot." /> : <ResearchTerminal key={bundle.content_sha256} bundle={bundle} onDownload={download} />}</TabsContent>
        <TabsContent value="global"><GlobalIntelligence context={context} state={contextState} now={now} /></TabsContent>
        <TabsContent value="sources">{bundle ? <SourceCenter bundle={bundle} context={context} now={now} /> : <EmptyState title="No lineage loaded" copy="Load a research artifact to inspect provenance." />}</TabsContent>
        <TabsContent value="method"><Methodology /></TabsContent>
      </Tabs>
    </main>
    <footer><span>Aurum Spread v0.2.0 · Hack in Hills ’26</span><span>Research and education only · No broker execution</span></footer>
  </div></TooltipProvider>
}

export default App
