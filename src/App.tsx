import { useMemo, useState } from 'react'
import {
  Activity, ArrowDownRight, ArrowUpRight, BookOpen, CalendarClock,
  CheckCircle2, CircleHelp, Code2, Database, Download, Info, Minus,
  RefreshCw, ShieldCheck, Sparkles, TrendingUp,
} from 'lucide-react'
import FadeContent from '@/components/FadeContent'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { pairs, snapshots, spreadSeries } from '@/data/demo'
import { formatIndianCurrency, formatNumber, normalizedFineGoldPrice } from '@/lib/analytics'
import './App.css'

type PairId = (typeof pairs)[number]['id']
const pairScale: Record<PairId, number> = {
  'GOLDTEN/GOLDM': 1,
  'GOLDGUINEA/GOLDM': 0.54,
  'GOLDPETAL/GOLDM': 0.26,
}

function SpreadChart({ pair }: { pair: PairId }) {
  const width = 840
  const height = 276
  const pad = { left: 45, right: 18, top: 18, bottom: 34 }
  const chartWidth = width - pad.left - pad.right
  const chartHeight = height - pad.top - pad.bottom
  const minY = -20
  const maxY = 20
  const series = spreadSeries.map((point) => ({ ...point, spreadBps: point.spreadBps * pairScale[pair] }))
  const x = (index: number) => pad.left + (index / (series.length - 1)) * chartWidth
  const y = (value: number) => pad.top + ((maxY - value) / (maxY - minY)) * chartHeight
  const path = series.map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(index).toFixed(1)} ${y(point.spreadBps).toFixed(1)}`).join(' ')
  const areaPath = `${path} L ${x(series.length - 1)} ${y(0)} L ${x(0)} ${y(0)} Z`
  const ticks = [-20, -10, 0, 10, 20]
  const labels = [0, 7, 15, 23, 31]
  const last = series.at(-1)!

  return (
    <div className="chart-wrap">
      <svg className="spread-chart" viewBox={`0 0 ${width} ${height}`} role="img">
        <title>{pair} normalized price spread</title>
        <desc>Daily purity-adjusted spread in basis points, with two-standard-deviation bands.</desc>
        <defs>
          <linearGradient id="area-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#bb8a21" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#bb8a21" stopOpacity="0" />
          </linearGradient>
        </defs>
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} className={tick === 0 ? 'chart-zero' : 'chart-grid'} />
            <text x={pad.left - 10} y={y(tick) + 4} textAnchor="end" className="chart-axis">{tick}</text>
          </g>
        ))}
        <line x1={pad.left} x2={width - pad.right} y1={y(14.1)} y2={y(14.1)} className="chart-band" />
        <line x1={pad.left} x2={width - pad.right} y1={y(-14.1)} y2={y(-14.1)} className="chart-band" />
        <path d={areaPath} fill="url(#area-fill)" />
        <path d={path} className="chart-line" />
        <circle cx={x(series.length - 1)} cy={y(last.spreadBps)} r="4.5" className="chart-point" />
        {labels.map((index) => <text key={index} x={x(index)} y={height - 8} textAnchor="middle" className="chart-axis">{series[index].date}</text>)}
      </svg>
    </div>
  )
}

function MetricCard({ label, value, detail, tone = 'default', icon }: {
  label: string
  value: string
  detail: string
  tone?: 'default' | 'positive' | 'warning'
  icon: React.ReactNode
}) {
  return (
    <Card className={`metric-card tone-${tone}`}>
      <CardHeader><span className="metric-icon" aria-hidden="true">{icon}</span><span className="eyebrow">{label}</span></CardHeader>
      <CardContent><strong>{value}</strong><span>{detail}</span></CardContent>
    </Card>
  )
}

function Dashboard() {
  const [selectedPair, setSelectedPair] = useState<PairId>('GOLDTEN/GOLDM')
  const [lookback, setLookback] = useState('40')
  const selected = pairs.find((pair) => pair.id === selectedPair)!
  const expectedEdge = Math.max(0, selected.spread - 5.5)
  const estimatedCost = selectedPair === 'GOLDTEN/GOLDM' ? 12 : 16
  const actionable = selected.zScore >= 2 && expectedEdge > estimatedCost

  return (
    <FadeContent duration={450} threshold={0.05}>
      <section className="summary-row" aria-label="Current signal summary">
        <MetricCard label="Current spread" value={`${selected.spread.toFixed(1)} bps`} detail="Purity-adjusted fine gold" tone="warning" icon={<Activity size={16} />} />
        <MetricCard label="Walk-forward z-score" value={`${selected.zScore.toFixed(2)}σ`} detail={`${lookback}-session trailing window`} tone={selected.zScore >= 2 ? 'warning' : 'default'} icon={<TrendingUp size={16} />} />
        <MetricCard label="Edge after costs" value={`${(expectedEdge - estimatedCost).toFixed(1)} bps`} detail={`${estimatedCost} bps round-trip estimate`} tone={expectedEdge > estimatedCost ? 'positive' : 'default'} icon={expectedEdge > estimatedCost ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />} />
        <MetricCard label="Decision" value={actionable ? 'Actionable' : 'No trade'} detail={actionable ? 'All execution gates passed' : 'Cost gate blocks entry'} tone={actionable ? 'positive' : 'default'} icon={actionable ? <CheckCircle2 size={16} /> : <ShieldCheck size={16} />} />
      </section>

      <section className="analysis-grid">
        <Card className="chart-card">
          <CardHeader className="section-heading chart-heading">
            <div><div className="heading-line"><CardTitle>Relative-value monitor</CardTitle><Badge variant="outline">DEMO DATA</Badge></div><p>Normalized ₹ per gram of fine gold · spread in basis points</p></div>
            <div className="chart-controls">
              <label><span className="sr-only">Contract pair</span><NativeSelect value={selectedPair} onChange={(event) => setSelectedPair(event.target.value as PairId)}>{pairs.map((pair) => <NativeSelectOption key={pair.id} value={pair.id}>{pair.id}</NativeSelectOption>)}</NativeSelect></label>
              <div className="segmented" aria-label="Lookback window">
                {['20', '40', '60'].map((value) => <button key={value} type="button" className={lookback === value ? 'active' : ''} onClick={() => setLookback(value)} aria-pressed={lookback === value}>{value}d</button>)}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <SpreadChart pair={selectedPair} />
            <div className="chart-legend" aria-label="Chart legend"><span><i className="legend-line" /> normalized spread</span><span><i className="legend-dash" /> ±2σ training band</span><span><i className="legend-zero" /> parity</span></div>
          </CardContent>
        </Card>

        <Card className="decision-card">
          <CardHeader className="section-heading"><div><span className="eyebrow">Signal decision</span><CardTitle>{actionable ? 'Entry approved' : 'Observe, do not enter'}</CardTitle></div><span className={`status-light ${actionable ? 'go' : ''}`} aria-hidden="true" /></CardHeader>
          <CardContent>
            <div className="trade-expression"><div><span>Long</span><strong>{selected.long}</strong></div><div className="trade-divider"><Minus size={16} /></div><div><span>Short</span><strong>{selected.short}</strong></div></div>
            <div className="gate-list">
              <div><CheckCircle2 size={15} /><span>Statistical gate</span><strong>{selected.zScore.toFixed(2)}σ</strong></div>
              <div><CheckCircle2 size={15} /><span>Expiry gate</span><strong>15 DTE</strong></div>
              <div><CheckCircle2 size={15} /><span>Liquidity gate</span><strong>Pass</strong></div>
              <div className={actionable ? '' : 'blocked'}><ShieldCheck size={15} /><span>Cost gate</span><strong>{actionable ? 'Pass' : 'Blocked'}</strong></div>
            </div>
            <div className="decision-note"><Info size={15} /><p>Expected convergence is {expectedEdge.toFixed(1)} bps versus {estimatedCost} bps estimated round-trip cost. The alert stays quiet until edge clears cost plus safety buffer.</p></div>
          </CardContent>
        </Card>
      </section>

      <section className="lower-grid">
        <Card className="contracts-card">
          <CardHeader className="section-heading">
            <div><CardTitle>Contract monitor</CardTitle><p>Latest eligible expiry for each instrument</p></div>
            <Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon-sm" aria-label="About normalized prices"><CircleHelp size={16} /></Button></TooltipTrigger><TooltipContent sideOffset={8}>Close ÷ quote grams ÷ purity</TooltipContent></Tooltip>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>Contract</TableHead><TableHead>Expiry</TableHead><TableHead className="numeric">Normalized ₹/g</TableHead><TableHead className="numeric">Volume</TableHead><TableHead className="numeric">Open interest</TableHead><TableHead>Status</TableHead></TableRow></TableHeader>
              <TableBody>{snapshots.map((contract) => <TableRow key={contract.symbol}>
                <TableCell><strong>{contract.symbol}</strong><span className="cell-note">{contract.tradingUnitGrams}g lot · {(contract.purity * 1000).toFixed(0)} purity</span></TableCell>
                <TableCell>{contract.expiry}<span className="cell-note">{contract.daysToExpiry} days</span></TableCell>
                <TableCell className="numeric mono">{formatIndianCurrency(normalizedFineGoldPrice(contract), 2)}</TableCell>
                <TableCell className="numeric mono">{formatNumber(contract.volume)}</TableCell>
                <TableCell className="numeric mono">{formatNumber(contract.openInterest)}</TableCell>
                <TableCell><Badge variant="outline" className={contract.volume < 500 ? 'badge-watch' : 'badge-pass'}>{contract.volume < 500 ? 'THIN' : 'ELIGIBLE'}</Badge></TableCell>
              </TableRow>)}</TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="backtest-card">
          <CardHeader className="section-heading"><div><CardTitle>Walk-forward proof</CardTitle><p>Illustrative holdout · costs included</p></div><Badge variant="outline">UNSEEN 30%</Badge></CardHeader>
          <CardContent>
            <div className="backtest-hero"><span>Net strategy return</span><strong>+0.9%</strong><small>Gold beta 0.04</small></div>
            <div className="attribution"><div><span>Gross convergence</span><strong className="positive">+3.8%</strong></div><div><span>Fees + slippage</span><strong className="negative">−2.9%</strong></div><div><span>Maximum drawdown</span><strong>−1.6%</strong></div><div><span>Completed trades</span><strong>18</strong></div></div>
            <p className="fine-print">Illustrative metrics from synthetic demo data. Production claims require the downloaded MCX history and frozen test window.</p>
          </CardContent>
        </Card>
      </section>
    </FadeContent>
  )
}

function Methodology() {
  const steps = [
    ['01', 'Validate', 'Reject stale responses by comparing the returned Date with the requested trading day. Trim padded symbols and parse expiry explicitly.'],
    ['02', 'Normalize', 'Convert every close to rupees per gram of fine gold using quotation base and purity—not merely trading-unit size.'],
    ['03', 'Align', 'Match observations by date and actual expiry. Never splice a continuous near-month series across rolls.'],
    ['04', 'Score', 'Estimate rolling mean and volatility using only information available before each decision. Produce a lagged z-score.'],
    ['05', 'Gate', 'Require sufficient volume, open interest, days to expiry, and expected convergence above all-in transaction costs.'],
    ['06', 'Attribute', 'Report gross spread convergence, costs, net return, and residual gold beta separately.'],
  ]
  return <section className="method-page"><div className="page-intro"><span className="eyebrow">Research design</span><h2>A signal that is allowed to say “nothing today.”</h2><p>The product is optimized for defensibility. Every output carries its lineage, eligibility gates, and an explanation of what would invalidate it.</p></div><div className="method-grid">{steps.map(([number, title, copy]) => <Card key={number} className="method-card"><CardContent><span>{number}</span><h3>{title}</h3><p>{copy}</p></CardContent></Card>)}</div><Card className="formula-card"><CardHeader><CardTitle>Core normalization</CardTitle></CardHeader><CardContent><code>fine_gold_price = close_price ÷ quoted_grams ÷ purity_fraction</code><p>Example: GOLDM uses a 10g quotation base and 0.995 purity; GOLDTEN uses 10g and 0.999. This makes the values economically comparable before measuring a spread.</p></CardContent></Card></section>
}

function DataNotes() {
  return <section className="data-page"><div className="page-intro"><span className="eyebrow">Data contract</span><h2>Exchange data in, auditable evidence out.</h2><p>The demo is intentionally synthetic. The production pipeline accepts exported MCX Bhavcopy rows and preserves the raw observation beside every derived value.</p></div><div className="source-grid">
    <Card><CardHeader><Database size={18} /><CardTitle>Daily Bhavcopy</CardTitle></CardHeader><CardContent><p>OHLC, previous close, volume, value, and open interest at contract level. Available from November 2003.</p><a href="https://www.mcxindia.com/market-data/bhavcopy" target="_blank" rel="noreferrer">Open official source <ArrowUpRight size={14} /></a></CardContent></Card>
    <Card><CardHeader><BookOpen size={18} /><CardTitle>Contract specifications</CardTitle></CardHeader><CardContent><p>Trading units, quotation bases, deliverable purity, expiry rules, and current circular-linked specifications.</p><a href="https://www.mcxindia.com/products/bullion/gold" target="_blank" rel="noreferrer">Open official source <ArrowUpRight size={14} /></a></CardContent></Card>
    <Card><CardHeader><CalendarClock size={18} /><CardTitle>Lifecycle controls</CardTitle></CardHeader><CardContent><p>Every intended entry and exit must fit before tender and expiry restrictions. DTE gates are recorded with the signal.</p></CardContent></Card>
  </div><Card className="warning-card"><CardContent><ShieldCheck size={20} /><div><h3>Execution caveat</h3><p>Settlement prices are official reference values, not guaranteed fills. Volume is activity, not available market depth. The system therefore presents research intelligence—not an execution promise.</p></div></CardContent></Card></section>
}

function App() {
  const [lastRefresh, setLastRefresh] = useState('14 Oct 2026 · 23:42 IST')
  const refresh = () => setLastRefresh(`Demo refreshed · ${new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`)
  const dateStamp = useMemo(() => lastRefresh, [lastRefresh])
  return <TooltipProvider><div className="app-shell">
    <header className="topbar"><div className="brand-block"><div className="brand-mark" aria-hidden="true">Au</div><div><strong>Aurum Spread</strong><span>MCX relative-value intelligence</span></div></div><div className="header-actions"><div className="data-state"><span /><div><strong>Research mode</strong><small>{dateStamp}</small></div></div><Button variant="outline" size="sm" onClick={refresh}><RefreshCw size={14} /> Refresh</Button><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon-sm" aria-label="Download research snapshot"><Download size={16} /></Button></TooltipTrigger><TooltipContent sideOffset={8}>Export snapshot (coming next)</TooltipContent></Tooltip></div></header>
    <main><section className="hero-copy"><div><span className="eyebrow"><Sparkles size={13} /> Commodity derivatives intelligence</span><h1>Find the spread.<br /><em>Prove the edge.</em></h1></div><p>A defensible monitor for price dislocations across MCX gold contract sizes—normalized for purity, filtered for liquidity, and tested without hindsight.</p></section>
      <Tabs defaultValue="monitor"><div className="nav-row"><TabsList variant="line" aria-label="Product sections"><TabsTrigger value="monitor">Monitor</TabsTrigger><TabsTrigger value="method">Methodology</TabsTrigger><TabsTrigger value="data">Data notes</TabsTrigger></TabsList><a className="repo-link" href="https://github.com" target="_blank" rel="noreferrer"><Code2 size={15} /> Repository</a></div><TabsContent value="monitor"><Dashboard /></TabsContent><TabsContent value="method"><Methodology /></TabsContent><TabsContent value="data"><DataNotes /></TabsContent></Tabs>
    </main>
    <footer><span>Aurum Spread v0.1.0 · Hack in Hills ’26</span><span>Research prototype · Not investment advice</span></footer>
  </div></TooltipProvider>
}

export default App
