import Link from 'next/link'
import { UserButton } from '@clerk/nextjs'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/workspace', label: 'Workspace' },
  { href: '/proof', label: 'Proof' },
  { href: '/alerts', label: 'Alerts' },
  { href: '/account', label: 'Account' },
]

export function AppShell({
  children,
  currentPath,
  title,
  subtitle,
  planLabel,
  buyerType,
}: {
  children: React.ReactNode
  currentPath: string
  title: string
  subtitle: string
  planLabel: string
  buyerType: string
}) {
  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#09090b_0%,#09090b_42%,#111827_100%)] text-zinc-100">
      <header className="sticky top-0 z-20 border-b border-white/10 bg-zinc-950/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4 lg:px-10">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="flex items-center gap-3">
              <span className="text-xl text-cyan-300">⬡</span>
              <div>
                <p className="font-mono text-sm tracking-[0.35em] text-zinc-200">ORION</p>
                <p className="text-[11px] uppercase tracking-[0.28em] text-zinc-500">{subtitle}</p>
              </div>
            </Link>
            <Badge variant="outline" className="border-cyan-400/30 bg-cyan-400/10 text-cyan-200 font-mono text-[10px]">
              {planLabel}
            </Badge>
            <Badge variant="outline" className="border-white/10 bg-white/5 text-zinc-300 font-mono text-[10px]">
              {buyerType.replace(/_/g, ' ')}
            </Badge>
          </div>
          <div className="flex items-center gap-3">
            <nav className="hidden items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1 md:flex">
              {navItems.map(item => {
                const active = currentPath === item.href
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'rounded-full px-3 py-1.5 text-sm text-zinc-400 transition-colors',
                      active ? 'bg-cyan-300 text-zinc-950' : 'hover:bg-white/10 hover:text-zinc-200'
                    )}
                  >
                    {item.label}
                  </Link>
                )
              })}
            </nav>
            <UserButton />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
        <div className="mb-6">
          <h1 className="text-3xl font-semibold text-white">{title}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-400">{subtitle}</p>
        </div>
        {children}
      </main>
    </div>
  )
}
