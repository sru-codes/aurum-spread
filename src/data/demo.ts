export type ContractCode = 'GOLDM' | 'GOLDTEN' | 'GOLDGUINEA' | 'GOLDPETAL'

export interface ContractSnapshot {
  symbol: ContractCode
  expiry: string
  close: number
  quoteGrams: number
  tradingUnitGrams: number
  purity: number
  volume: number
  openInterest: number
  daysToExpiry: number
}

export interface SpreadPoint {
  date: string
  spreadBps: number
  zScore: number
  upperBand: number
  lowerBand: number
}

export const snapshots: ContractSnapshot[] = [
  {
    symbol: 'GOLDM',
    expiry: '05 NOV 2026',
    close: 124_862,
    quoteGrams: 10,
    tradingUnitGrams: 100,
    purity: 0.995,
    volume: 14_820,
    openInterest: 32_418,
    daysToExpiry: 22,
  },
  {
    symbol: 'GOLDTEN',
    expiry: '29 OCT 2026',
    close: 125_562,
    quoteGrams: 10,
    tradingUnitGrams: 10,
    purity: 0.999,
    volume: 1_264,
    openInterest: 4_892,
    daysToExpiry: 15,
  },
  {
    symbol: 'GOLDGUINEA',
    expiry: '29 OCT 2026',
    close: 100_377,
    quoteGrams: 8,
    tradingUnitGrams: 8,
    purity: 0.999,
    volume: 438,
    openInterest: 1_731,
    daysToExpiry: 15,
  },
  {
    symbol: 'GOLDPETAL',
    expiry: '29 OCT 2026',
    close: 12_542,
    quoteGrams: 1,
    tradingUnitGrams: 1,
    purity: 0.999,
    volume: 2_106,
    openInterest: 7_044,
    daysToExpiry: 15,
  },
]

const spreads = [
  -3.2, -1.6, 0.8, 3.4, 1.9, -0.4, -2.3, -1.1, 2.1, 4.8, 3.6, 1.4,
  -0.7, -3.1, -4.4, -2.2, 0.3, 2.8, 5.1, 7.3, 4.9, 2.7, 0.6, -1.8,
  -3.7, -1.9, 1.5, 4.2, 6.8, 9.4, 12.7, 15.8,
]

const dates = [
  '31 Aug', '01 Sep', '02 Sep', '03 Sep', '04 Sep', '07 Sep', '08 Sep', '09 Sep',
  '10 Sep', '11 Sep', '14 Sep', '15 Sep', '16 Sep', '17 Sep', '18 Sep', '21 Sep',
  '22 Sep', '23 Sep', '24 Sep', '25 Sep', '28 Sep', '29 Sep', '30 Sep', '01 Oct',
  '05 Oct', '06 Oct', '07 Oct', '08 Oct', '09 Oct', '12 Oct', '13 Oct', '14 Oct',
]

export const spreadSeries: SpreadPoint[] = spreads.map((spreadBps, index) => ({
  date: dates[index],
  spreadBps,
  zScore: Number((spreadBps / 7.05).toFixed(2)),
  upperBand: 14.1,
  lowerBand: -14.1,
}))

export const pairs = [
  { id: 'GOLDTEN/GOLDM', long: 'GOLDM', short: 'GOLDTEN', spread: 15.8, zScore: 2.24, status: 'Watch' },
  { id: 'GOLDGUINEA/GOLDM', long: 'GOLDM', short: 'GOLDGUINEA', spread: 8.6, zScore: 1.18, status: 'Neutral' },
  { id: 'GOLDPETAL/GOLDM', long: 'GOLDM', short: 'GOLDPETAL', spread: 4.1, zScore: 0.58, status: 'Neutral' },
] as const

