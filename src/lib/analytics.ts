import type { ContractSnapshot } from '../data/demo'

export function normalizedFineGoldPrice(contract: ContractSnapshot): number {
  return contract.close / (contract.quoteGrams * contract.purity)
}

export function relativeSpreadBps(candidate: ContractSnapshot, reference: ContractSnapshot): number {
  return (normalizedFineGoldPrice(candidate) / normalizedFineGoldPrice(reference) - 1) * 10_000
}

export function formatIndianCurrency(value: number, decimals = 0): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals,
  }).format(value)
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-IN').format(value)
}

