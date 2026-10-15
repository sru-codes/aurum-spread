import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchGoldApiSnapshot, type GoldApiSnapshot } from '@/lib/gold-api'

export type GoldApiLoadState = 'loading' | 'ready' | 'error'

export function useGoldApi() {
  const [snapshot, setSnapshot] = useState<GoldApiSnapshot | null>(null)
  const [state, setState] = useState<GoldApiLoadState>('loading')
  const [error, setError] = useState<string | null>(null)
  const snapshotRef = useRef<GoldApiSnapshot | null>(null)

  const refresh = useCallback(async () => {
    if (!snapshotRef.current) setState('loading')
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 12_000)
    try {
      const next = await fetchGoldApiSnapshot(controller.signal)
      snapshotRef.current = next
      setSnapshot(next)
      setState('ready')
      setError(null)
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Could not read the Gold API snapshot.'
      setError(message)
      if (!snapshotRef.current) setState('error')
    } finally {
      window.clearTimeout(timeout)
    }
  }, [])

  useEffect(() => {
    // This effect owns a scheduled external data refresh.
    // oxlint-disable-next-line react/set-state-in-effect
    void refresh()
    const interval = window.setInterval(() => void refresh(), 60_000)
    return () => window.clearInterval(interval)
  }, [refresh])

  return { snapshot, state, error, refresh }
}
