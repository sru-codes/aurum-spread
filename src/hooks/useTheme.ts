import { useEffect, useState } from 'react'

export type ThemePreference = 'system' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

const STORAGE_KEY = 'aurum-theme'
const COLOR_SCHEME_QUERY = '(prefers-color-scheme: dark)'

function parsePreference(value: string | null): ThemePreference {
  return value === 'light' || value === 'dark' ? value : 'system'
}

function readPreference(): ThemePreference {
  try {
    return parsePreference(window.localStorage.getItem(STORAGE_KEY))
  } catch {
    return 'system'
  }
}

function readSystemTheme(): ResolvedTheme {
  return window.matchMedia(COLOR_SCHEME_QUERY).matches ? 'dark' : 'light'
}

export function useTheme() {
  const [preference, setPreference] = useState<ThemePreference>(readPreference)
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(readSystemTheme)
  const theme = preference === 'system' ? systemTheme : preference

  useEffect(() => {
    const mediaQuery = window.matchMedia(COLOR_SCHEME_QUERY)
    const handleSystemTheme = (event: MediaQueryListEvent) => setSystemTheme(event.matches ? 'dark' : 'light')
    const handleStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY || event.key === null) setPreference(parsePreference(event.newValue))
    }
    mediaQuery.addEventListener('change', handleSystemTheme)
    window.addEventListener('storage', handleStorage)
    return () => {
      mediaQuery.removeEventListener('change', handleSystemTheme)
      window.removeEventListener('storage', handleStorage)
    }
  }, [])

  useEffect(() => {
    const root = document.documentElement
    root.dataset.theme = theme
    root.style.colorScheme = theme
    const themeColor = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
    if (themeColor) themeColor.content = theme === 'dark' ? '#141512' : '#f3f0e8'
    try {
      if (preference === 'system') window.localStorage.removeItem(STORAGE_KEY)
      else window.localStorage.setItem(STORAGE_KEY, preference)
    } catch {
      // The active theme still works for this page if browser storage is unavailable.
    }
  }, [preference, theme])

  const cycleTheme = () => {
    setPreference((current) => current === 'system' ? 'light' : current === 'light' ? 'dark' : 'system')
  }

  const nextPreference = preference === 'system' ? 'light' : preference === 'light' ? 'dark' : 'system'
  const description = preference === 'system'
    ? `System theme (${theme}); switch to light`
    : `${preference[0].toUpperCase()}${preference.slice(1)} theme; switch to ${nextPreference}`

  return { preference, theme, cycleTheme, description }
}
