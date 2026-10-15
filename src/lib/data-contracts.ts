export type DataMode = 'DEMO' | 'VERIFIED_HISTORICAL'

export interface ObservationJson {
  trading_date: string
  expiry_date: string
  symbol: string
  close: string
  volume: number
  open_interest: number
  fine_gold_price: string
  lot_notional: string
}

export interface GateJson {
  name: string
  passed: boolean
  observed: string
  threshold: string
}

export interface ResearchPointJson {
  trading_date: string
  candidate: ObservationJson
  reference: ObservationJson
  raw_spread_bps: number
  expiry_carry_bps: number
  residual_spread_bps: number
  zscore: number | null
  trailing_mean_bps: number | null
  trailing_stdev_bps: number | null
  liquidity_state: string
  market_state: string
  gates: GateJson[]
  eligible: boolean
  verdict: string
  partition: 'train' | 'validation' | 'test'
}

export interface DailyAttributionJson {
  trading_date: string
  position: number
  gross_pnl_inr: number
  relative_convergence_pnl_inr: number
  gold_exposure_pnl_inr: number
  unexplained_residual_pnl_inr: number
  brokerage_inr: number
  fees_inr: number
  slippage_inr: number
  funding_inr: number
  net_pnl_inr: number
  action: string
}

export interface SimulationJson {
  hedge_ratio: {
    candidate_lots: number
    reference_lots: number
    candidate_fine_grams: string
    reference_fine_grams: string
    net_fine_gold_grams: string
  }
  daily: DailyAttributionJson[]
  trades: number
  gross_pnl_inr: number
  relative_convergence_pnl_inr: number
  gold_exposure_pnl_inr: number
  unexplained_residual_pnl_inr: number
  brokerage_inr: number
  fees_inr: number
  slippage_inr: number
  funding_inr: number
  net_pnl_inr: number
  max_drawdown_inr: number
}

export interface ResearchSnapshot {
  schema_version: string
  engine_version: string
  mode: DataMode
  content_sha256: string
  pair: {
    candidate_symbol: string
    candidate_expiry: string
    reference_symbol: string
    reference_expiry: string
  }
  contract_specifications: {
    candidate: ContractSpecJson
    reference: ContractSpecJson
  }
  configuration: {
    lookback_sessions: number
    entry_z: number
    exit_z: number
    annual_carry_bps: number
  }
  cost_assumptions: Record<string, number>
  lineage: Record<string, unknown>
  methodology: Record<string, string>
  series: ResearchPointJson[]
  simulation: SimulationJson
  partition_simulations: Record<'train' | 'validation' | 'test', SimulationJson>
  partition_cost_sensitivity: Record<'train' | 'validation' | 'test', Array<{
    slippage_bps: number
    gross_pnl_inr: number
    total_cost_inr: number
    net_pnl_inr: number
  }>>
  cost_sensitivity: Array<{
    slippage_bps: number
    gross_pnl_inr: number
    total_cost_inr: number
    net_pnl_inr: number
  }>
}

export interface ContractSpecJson {
  symbol: string
  trading_unit_grams: string
  quoted_grams: string
  purity: string
  last_trading_day_rule: string
  tender_period_sessions: number
  effective_expiry_from: string
  source_url: string
}

export interface ContractSummary {
  symbol: string
  trading_date: string
  expiry_date: string
  close: string
  fine_gold_price_per_gram: string
  volume_lots: number
  open_interest_lots: number
  days_to_expiry: number
  trading_unit_grams: number
  quoted_grams: number
  purity: number
}

export interface ResearchBundle {
  schema_version: string
  engine_version: string
  mode: DataMode
  content_sha256: string
  generated_at_utc: string
  latest_observation_date: string
  disclaimer: string
  contracts: ContractSummary[]
  analyses: Record<string, Record<string, ResearchSnapshot>>
}

export interface ProviderHealth {
  id: string
  status: string
  last_successful_update: string | null
  latest_observation: string | null
  authentication: string
  coverage: string
  limitations: string
  error_code?: string
}

export interface ContextSnapshot {
  schema_version: string
  engine_version: string
  generated_at_utc: string
  mode: 'SUPPLEMENTARY_REFERENCE'
  content_sha256: string
  providers: ProviderHealth[]
  international: {
    gold_spot?: {
      price_usd_per_troy_ounce: string
      price_usd_per_gram: string
      computed_at_utc: string
      is_stale: boolean
      source_url: string
    }
    usd_inr?: {
      rate: string
      requested_date: string
      effective_date: string
      source_url: string
    }
    gold_reference_inr_per_gram?: {
      value: string
      calculation: string
      gold_timestamp_utc: string
      fx_effective_date: string
      classification: string
    }
  }
}

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function nonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0
}

export function parseResearchSnapshot(value: unknown): ResearchSnapshot {
  if (!object(value)) throw new Error('Snapshot must be a JSON object.')
  if (value.mode !== 'DEMO' && value.mode !== 'VERIFIED_HISTORICAL') throw new Error('Unknown research mode.')
  if (!nonEmptyString(value.schema_version) || !nonEmptyString(value.engine_version)) throw new Error('Missing schema or engine version.')
  if (!nonEmptyString(value.content_sha256) || value.content_sha256.length !== 64) throw new Error('Missing SHA-256 content identity.')
  if (!object(value.lineage)) throw new Error('Missing dataset lineage.')
  if (value.mode === 'VERIFIED_HISTORICAL' && (!nonEmptyString(value.lineage.dataset_id) || !nonEmptyString(value.lineage.clean_content_sha256) || !object(value.lineage.source_lineage))) {
    throw new Error('Verified historical snapshots must include clean-dataset identity and source lineage.')
  }
  if (value.mode === 'DEMO' && !nonEmptyString(value.lineage.classification)) throw new Error('Demo snapshots must identify their synthetic classification.')
  if (!object(value.pair)) throw new Error('Missing explicit contract pair and expiries.')
  for (const field of ['candidate_symbol', 'candidate_expiry', 'reference_symbol', 'reference_expiry']) {
    if (!nonEmptyString(value.pair[field])) throw new Error(`Missing pair field: ${field}.`)
  }
  if (!object(value.contract_specifications) || !object(value.contract_specifications.candidate) || !object(value.contract_specifications.reference)) throw new Error('Missing effective-dated contract specifications.')
  if (!object(value.configuration) || typeof value.configuration.lookback_sessions !== 'number') throw new Error('Missing research configuration.')
  if (!Array.isArray(value.series) || value.series.length === 0) throw new Error('Research series is empty.')
  if (!object(value.simulation) || !object(value.partition_simulations) || !object(value.partition_cost_sensitivity) || !Array.isArray(value.cost_sensitivity)) throw new Error('Missing simulation or sensitivity output.')
  if (!object(value.partition_simulations.test) || !Array.isArray(value.partition_cost_sensitivity.test) || value.partition_cost_sensitivity.test.length === 0) throw new Error('Missing untouched test-partition results.')
  for (const point of value.series) {
    if (!object(point) || !nonEmptyString(point.trading_date) || !object(point.candidate) || !object(point.reference)) throw new Error('Invalid research point.')
    if (typeof point.raw_spread_bps !== 'number' || typeof point.residual_spread_bps !== 'number' || !Array.isArray(point.gates)) throw new Error('Invalid spread calculation trace.')
  }
  return value as unknown as ResearchSnapshot
}

export function parseResearchBundle(value: unknown): ResearchBundle {
  if (!object(value)) throw new Error('Research bundle must be a JSON object.')
  if (value.mode !== 'DEMO' && value.mode !== 'VERIFIED_HISTORICAL') throw new Error('Unknown bundle mode.')
  if (!Array.isArray(value.contracts) || !object(value.analyses)) throw new Error('Bundle is missing contracts or analyses.')
  if (typeof value.content_sha256 !== 'string' || !/^[a-f\d]{64}$/i.test(value.content_sha256)) throw new Error('Bundle is missing its SHA-256 content identity.')
  for (const windows of Object.values(value.analyses)) {
    if (!object(windows)) throw new Error('Invalid analysis map.')
    for (const snapshot of Object.values(windows)) parseResearchSnapshot(snapshot)
  }
  return value as unknown as ResearchBundle
}

export function parseContextSnapshot(value: unknown): ContextSnapshot {
  if (!object(value) || value.mode !== 'SUPPLEMENTARY_REFERENCE') throw new Error('Invalid contextual snapshot.')
  if (!Array.isArray(value.providers) || !object(value.international)) throw new Error('Context snapshot is incomplete.')
  return value as unknown as ContextSnapshot
}

export function bundleFromSnapshot(snapshot: ResearchSnapshot): ResearchBundle {
  const latest = snapshot.series.at(-1)!
  const pairId = `${snapshot.pair.candidate_symbol}/${snapshot.pair.reference_symbol}`
  const contracts = ([
    ['candidate', latest.candidate],
    ['reference', latest.reference],
  ] as const).map(([leg, item]) => {
    const spec = snapshot.contract_specifications[leg]
    return {
      symbol: item.symbol,
      trading_date: item.trading_date,
      expiry_date: item.expiry_date,
      close: item.close,
      fine_gold_price_per_gram: item.fine_gold_price,
      volume_lots: item.volume,
      open_interest_lots: item.open_interest,
      days_to_expiry: Math.round((Date.parse(item.expiry_date) - Date.parse(item.trading_date)) / 86_400_000),
      trading_unit_grams: Number(spec.trading_unit_grams),
      quoted_grams: Number(spec.quoted_grams),
      purity: Number(spec.purity),
    }
  })
  return {
    schema_version: snapshot.schema_version,
    engine_version: snapshot.engine_version,
    mode: snapshot.mode,
    content_sha256: snapshot.content_sha256,
    generated_at_utc: latest.trading_date,
    latest_observation_date: latest.trading_date,
    disclaimer: 'User-loaded engine snapshot. Schema checked in the browser; verify lineage files before empirical use.',
    contracts,
    analyses: { [pairId]: { [String(snapshot.configuration.lookback_sessions)]: snapshot } },
  }
}
