'use client'

import { Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'

const LINKS = [
  { href: '#how-it-works', label: 'How it works' },
  { href: '#analyse', label: 'Analyse' },
  { href: '#performance', label: 'Performance' },
  { href: '#scope', label: 'Scope' },
]

export function SiteHeader() {
  const { resolvedTheme, setTheme } = useTheme()
  const isDark = resolvedTheme !== 'light'

  return (
    <header className="glass fixed inset-x-0 top-0 z-50 border-x-0 border-t-0">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <a href="#top" className="flex items-center gap-2 font-semibold tracking-tight">
          <span aria-hidden="true" className="flex size-6 items-center justify-center rounded-md bg-foreground">
            <span className="size-2 rounded-full bg-enzyme" />
            <span className="-ml-0.5 size-2 rounded-full bg-non-enzyme" />
          </span>
          ProtClass
        </a>
        <nav aria-label="Primary" className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className="transition-colors hover:text-foreground">
              {l.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            onClick={() => setTheme(isDark ? 'light' : 'dark')}
          >
            <Sun className="hidden size-4 dark:block" />
            <Moon className="size-4 dark:hidden" />
          </Button>
          <Button size="sm" render={<a href="#analyse" />} nativeButton={false}>
            Analyse
          </Button>
        </div>
      </div>
    </header>
  )
}
