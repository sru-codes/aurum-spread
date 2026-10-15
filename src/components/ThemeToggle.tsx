import { Monitor, Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/hooks/useTheme'

export default function ThemeToggle({ className = '' }: { className?: string }) {
  const { preference, theme, cycleTheme, description } = useTheme()
  const icon = preference === 'system' ? <Monitor aria-hidden="true" /> : theme === 'dark' ? <Moon aria-hidden="true" /> : <Sun aria-hidden="true" />

  return <Button
    variant="ghost"
    size="icon-sm"
    className={`theme-toggle ${className}`}
    onClick={cycleTheme}
    aria-label={`${description}. Activate to change theme.`}
    title={`${description}. Activate to change theme.`}
    data-theme-preference={preference}
  >
    {icon}
  </Button>
}
