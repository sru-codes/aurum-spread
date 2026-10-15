import assert from 'node:assert/strict'
import test from 'node:test'
import { parseGoldApiSnapshot } from './gold-api.ts'

const section = (data: unknown) => ({ data, status: data ? 'ok' : 'error', error: null, source_url: null, fetched_at_utc: '2026-10-15T14:00:00Z' })
type SnapshotFixture = {
  mode: string
  sections: Record<'gold' | 'fx' | 'bars' | 'macro' | 'news', ReturnType<typeof section>>
  [key: string]: unknown
}

function snapshot(): SnapshotFixture {
  return {
    schema_version: '1', engine_version: '1.0.0', service: 'gold-api',
    generated_at_utc: '2026-10-15T14:01:00Z', mode: 'LIVE', refresh_interval_seconds: 60,
    sections: {
      gold: section({ symbol: 'XAU-USD-SPOT', price_usd_per_troy_ounce: '4100.00', price_usd_per_gram: '131.82', computed_at_utc: '2026-10-15T13:45:00Z', is_stale: false, sources: [], unit: 'troy_ounce' }),
      fx: section({ base: 'USD', quote: 'INR', rate: '95.12', requested_date: '2026-10-15', effective_date: '2026-10-15' }),
      bars: section({ symbol: 'XAU-USD-SPOT', interval: '1d', from: '2026-10-14', to: '2026-10-14', count: 1, bars: [{ bar_start_utc: '2026-10-14T00:00:00Z', open_usd_per_troy_ounce: '4000', high_usd_per_troy_ounce: '4200', low_usd_per_troy_ounce: '3900', close_usd_per_troy_ounce: '4100', is_closed: true }] }),
      macro: section({ series: { DGS10: [{ date: '2026-10-14', value: '4.12' }] } }),
      news: section({ articles: [{ title: 'Gold context', url: 'https://news.example/story', published_at_utc: '2026-10-15T13:00:00Z', source: 'News' }] }),
    },
    derived: { gold_reference_inr_per_gram: { value: '12540.00', gold_usd_per_troy_ounce: '4100.00', usd_inr: '95.12', calculation: 'XAU/USD / 31.1034768 * USD/INR', gold_source: 'goldprice.dev', fx_source: 'Frankfurter', classification: 'context only' } },
    providers: [{ id: 'goldprice.dev', status: 'available' }],
  }
}

test('gold API parser accepts a versioned snapshot with explicit units and closed bars', () => {
  const parsed = parseGoldApiSnapshot(snapshot())
  assert.equal(parsed.sections.gold.data?.unit, 'troy_ounce')
  assert.equal(parsed.sections.bars.data?.bars.length, 1)
  assert.equal(parsed.derived.gold_reference_inr_per_gram?.value, '12540.00')
})

test('gold API parser allows partial snapshots with unavailable section data', () => {
  const input = snapshot()
  input.mode = 'PARTIAL'
  input.sections.gold = section(null)
  const parsed = parseGoldApiSnapshot(input)
  assert.equal(parsed.sections.gold.data, null)
  assert.equal(parsed.mode, 'PARTIAL')
})

test('gold API parser rejects incorrect commodity units and malformed bars', () => {
  const wrongUnit = snapshot()
  wrongUnit.sections.gold = section({ ...(wrongUnit.sections.gold.data as Record<string, unknown>), unit: 'gram' })
  assert.throws(() => parseGoldApiSnapshot(wrongUnit), /gold data is invalid/)

  const malformedBars = snapshot()
  const bars = malformedBars.sections.bars.data as Record<string, unknown>
  const [firstBar] = bars.bars as Array<Record<string, unknown>>
  malformedBars.sections.bars = section({ ...bars, count: 1, bars: [{ ...firstBar, is_closed: false }] })
  assert.throws(() => parseGoldApiSnapshot(malformedBars), /bars data is invalid/)
})

test('gold API parser rejects non-HTTPS news links', () => {
  const input = snapshot()
  input.sections.news = section({ articles: [{ title: 'Unsafe', url: 'javascript:alert(1)', published_at_utc: '2026-10-15T13:00:00Z', source: 'News' }] })
  assert.throws(() => parseGoldApiSnapshot(input), /news data is invalid/)
})
