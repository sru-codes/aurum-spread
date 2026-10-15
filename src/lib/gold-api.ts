export interface GoldApiSection<T> {
  data: T | null
  status: string
  error: { code?: string, message?: string } | null
  source_url: string | null
  fetched_at_utc: string | null
}

export interface GoldApiSpot {
  symbol: 'XAU-USD-SPOT'
  price_usd_per_troy_ounce: string
  price_usd_per_gram: string
  computed_at_utc: string
  is_stale: boolean
  sources: Array<{ source?: string, display_name?: string, fetched_at?: string }>
  unit: 'troy_ounce'
}

export interface GoldApiFx {
  base: 'USD'
  quote: 'INR'
  rate: string
  requested_date: string
  effective_date: string
}

export interface GoldApiBar {
  bar_start_utc: string
  open_usd_per_troy_ounce: string
  high_usd_per_troy_ounce: string
  low_usd_per_troy_ounce: string
  close_usd_per_troy_ounce: string
  is_closed: true
}

export interface GoldApiNewsArticle {
  title: string
  url: string
  published_at_utc: string
  source: string
  description?: string | null
}

export interface GoldApiProvider {
  id: string
  status: string
  authentication?: string
  last_successful_update?: string | null
  latest_observation?: string | null
  coverage?: string
  limitations?: string
  error_code?: string
}

export interface GoldApiSnapshot {
  schema_version: string
  engine_version: string
  service: string
  generated_at_utc: string
  mode: 'LIVE' | 'PARTIAL' | 'DEGRADED'
  refresh_interval_seconds: number
  sections: {
    gold: GoldApiSection<GoldApiSpot>
    fx: GoldApiSection<GoldApiFx>
    bars: GoldApiSection<{ symbol: string, interval: string, from: string, to: string, count: number, bars: GoldApiBar[] }>
    macro: GoldApiSection<{ series: Record<string, Array<{ date: string, value: string | null }>>, note?: string }>
    news: GoldApiSection<{ articles: GoldApiNewsArticle[], count?: number, note?: string }>
  }
  derived: {
    gold_reference_inr_per_gram?: {
      value: string
      gold_usd_per_troy_ounce: string
      usd_inr: string
      calculation: string
      gold_source: string
      fx_source: string
      classification: string
    }
  }
  providers: GoldApiProvider[]
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isDateTime(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0 && Number.isFinite(Date.parse(value))
}

function isPositiveNumber(value: unknown): value is string {
  return typeof value === 'string' && Number.isFinite(Number(value)) && Number(value) > 0
}

function isStrictlyIncreasing(values: string[]): boolean {
  return values.every((value, index) => index === 0 || Date.parse(value) > Date.parse(values[index - 1]))
}

function validateSection<T>(value: unknown, name: string, validateData: (data: unknown) => data is T): GoldApiSection<T> {
  if (!isObject(value) || typeof value.status !== 'string') throw new Error(`Gold API ${name} section is invalid.`)
  const data = value.data
  if (data !== null && data !== undefined && !validateData(data)) throw new Error(`Gold API ${name} data is invalid.`)
  return {
    data: data == null ? null : data,
    status: value.status,
    error: isObject(value.error) ? { code: typeof value.error.code === 'string' ? value.error.code : undefined, message: typeof value.error.message === 'string' ? value.error.message : undefined } : null,
    source_url: typeof value.source_url === 'string' ? value.source_url : null,
    fetched_at_utc: isDateTime(value.fetched_at_utc) ? value.fetched_at_utc : null,
  }
}

function isSpot(value: unknown): value is GoldApiSpot {
  return isObject(value)
    && value.symbol === 'XAU-USD-SPOT'
    && isPositiveNumber(value.price_usd_per_troy_ounce)
    && isPositiveNumber(value.price_usd_per_gram)
    && isDateTime(value.computed_at_utc)
    && typeof value.is_stale === 'boolean'
    && value.unit === 'troy_ounce'
}

function isFx(value: unknown): value is GoldApiFx {
  return isObject(value) && value.base === 'USD' && value.quote === 'INR'
    && isPositiveNumber(value.rate)
    && typeof value.requested_date === 'string' && Number.isFinite(Date.parse(value.requested_date))
    && typeof value.effective_date === 'string' && Number.isFinite(Date.parse(value.effective_date))
}

function isBar(value: unknown): value is GoldApiBar {
  if (!isObject(value) || !isDateTime(value.bar_start_utc) || value.is_closed !== true) return false
  const open = Number(value.open_usd_per_troy_ounce)
  const high = Number(value.high_usd_per_troy_ounce)
  const low = Number(value.low_usd_per_troy_ounce)
  const close = Number(value.close_usd_per_troy_ounce)
  return [open, high, low, close].every((number) => Number.isFinite(number) && number > 0)
    && high >= Math.max(open, close, low)
    && low <= Math.min(open, close, high)
}

function isBars(value: unknown): value is NonNullable<GoldApiSnapshot['sections']['bars']['data']> {
  if (!isObject(value) || value.symbol !== 'XAU-USD-SPOT' || value.interval !== '1d'
    || typeof value.from !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value.from)
    || typeof value.to !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value.to)
    || !Number.isFinite(Date.parse(value.from)) || !Number.isFinite(Date.parse(value.to))
    || typeof value.count !== 'number' || !Array.isArray(value.bars) || value.count !== value.bars.length
    || !value.bars.every(isBar)) return false
  if (value.from > value.to) return false
  const dates = value.bars.map((bar: GoldApiBar) => bar.bar_start_utc)
  return isStrictlyIncreasing(dates)
    && (!dates.length || (dates[0].slice(0, 10) >= value.from && dates.at(-1)!.slice(0, 10) <= value.to))
}

function isMacro(value: unknown): value is NonNullable<GoldApiSnapshot['sections']['macro']['data']> {
  return isObject(value) && isObject(value.series)
    && Object.values(value.series).every((series) => Array.isArray(series) && series.every((item) => isObject(item)
      && typeof item.date === 'string' && Number.isFinite(Date.parse(item.date))
      && (item.value === null || isPositiveNumber(item.value) || (typeof item.value === 'string' && Number.isFinite(Number(item.value)))))
      && isStrictlyIncreasing(series.map((item: { date: string }) => item.date))
    )
}

function isNews(value: unknown): value is NonNullable<GoldApiSnapshot['sections']['news']['data']> {
  return isObject(value) && Array.isArray(value.articles) && value.articles.every((article) => isObject(article)
    && typeof article.title === 'string' && typeof article.url === 'string'
    && (() => { try { return new URL(article.url).protocol === 'https:' } catch { return false } })()
    && isDateTime(article.published_at_utc) && typeof article.source === 'string')
}

export function parseGoldApiSnapshot(value: unknown): GoldApiSnapshot {
  if (!isObject(value) || !['LIVE', 'PARTIAL', 'DEGRADED'].includes(String(value.mode))) throw new Error('Gold API snapshot has an unknown mode.')
  if (typeof value.schema_version !== 'string' || typeof value.engine_version !== 'string'
    || typeof value.service !== 'string' || !isDateTime(value.generated_at_utc)
    || typeof value.refresh_interval_seconds !== 'number' || !isObject(value.sections)) {
    throw new Error('Gold API snapshot is missing version, timestamp, or section metadata.')
  }
  const providers: GoldApiProvider[] = Array.isArray(value.providers) ? value.providers.filter((provider): provider is GoldApiProvider => isObject(provider) && typeof provider.id === 'string' && typeof provider.status === 'string') : []
  const rawDerived = isObject(value.derived) ? value.derived.gold_reference_inr_per_gram : undefined
  const derived: GoldApiSnapshot['derived'] = {}
  if (isObject(rawDerived) && isPositiveNumber(rawDerived.value) && typeof rawDerived.calculation === 'string' && typeof rawDerived.classification === 'string') {
    derived.gold_reference_inr_per_gram = {
      value: String(rawDerived.value),
      gold_usd_per_troy_ounce: String(rawDerived.gold_usd_per_troy_ounce),
      usd_inr: String(rawDerived.usd_inr),
      calculation: rawDerived.calculation,
      gold_source: String(rawDerived.gold_source),
      fx_source: String(rawDerived.fx_source),
      classification: rawDerived.classification,
    }
  }
  return {
    schema_version: value.schema_version,
    engine_version: value.engine_version,
    service: value.service,
    generated_at_utc: value.generated_at_utc,
    mode: value.mode as GoldApiSnapshot['mode'],
    refresh_interval_seconds: value.refresh_interval_seconds,
    sections: {
      gold: validateSection(value.sections.gold, 'gold', isSpot),
      fx: validateSection(value.sections.fx, 'fx', isFx),
      bars: validateSection(value.sections.bars, 'bars', isBars),
      macro: validateSection(value.sections.macro, 'macro', isMacro),
      news: validateSection(value.sections.news, 'news', isNews),
    },
    derived,
    providers,
  }
}

const viteEnvironment = (import.meta as ImportMeta & { env?: { VITE_GOLD_API_URL?: string } }).env
export const GOLD_API_BASE_URL = (viteEnvironment?.VITE_GOLD_API_URL || 'https://goldapi.up.railway.app').replace(/\/$/, '')

export async function fetchGoldApiSnapshot(signal?: AbortSignal): Promise<GoldApiSnapshot> {
  const response = await fetch(`${GOLD_API_BASE_URL}/api/v1/snapshot`, {
    headers: { Accept: 'application/json' },
    cache: 'no-store',
    signal,
  })
  if (!response.ok) throw new Error(`Gold API returned HTTP ${response.status}.`)
  return parseGoldApiSnapshot(await response.json())
}
