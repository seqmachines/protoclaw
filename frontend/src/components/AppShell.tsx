import { Link, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { Database, GitCompareArrows, Menu, Upload, X } from 'lucide-react';

import { cn } from '@/lib/utils';
import { API_BASE_URL } from '@/lib/api';

const navItems = [
  { to: '/', label: 'Protocols', icon: Database },
  { to: '/reviews', label: 'Reviews', icon: GitCompareArrows },
  { to: '/submissions', label: 'Submissions', icon: Upload },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const connected = Boolean(API_BASE_URL);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b border-border/80 bg-card/92 backdrop-blur">
        <div className="mx-auto flex h-16 w-full max-w-7xl items-center gap-4 px-4">
          <Link to="/" className="flex shrink-0 items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center border border-border bg-background">
              <Database className="h-4 w-4" />
            </span>
            <div className="hidden sm:block">
              <p className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">
                Protoclaw Console
              </p>
              <p className="text-sm font-semibold tracking-[0.08em] text-foreground">
                Sequencing Protocol Registry
              </p>
            </div>
          </Link>

          <nav className="ml-4 hidden items-center gap-2 sm:flex">
            {navItems.map(({ to, label, icon: Icon }) => {
              const active = location.pathname === to;
              return (
                <Link
                  key={to}
                  to={to}
                  className={cn(
                    'inline-flex items-center gap-2 border px-3 py-2 text-xs font-medium uppercase tracking-[0.18em] transition-colors',
                    active
                      ? 'border-foreground bg-foreground text-background'
                      : 'border-border bg-background text-muted-foreground hover:border-foreground/40 hover:text-foreground',
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </Link>
              );
            })}
          </nav>

          <div className="flex-1" />

          <div className="hidden items-center gap-3 sm:flex">
            <div className="border border-border bg-background px-3 py-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {connected ? 'api linked' : 'api missing'}
            </div>
            <div className="flex items-center gap-2 border border-border bg-background px-3 py-2">
              <span
                className={cn(
                  'h-2 w-2 rounded-full',
                  connected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(74,222,128,0.5)]' : 'bg-zinc-400',
                )}
              />
              <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                {connected ? 'remote' : 'offline'}
              </span>
            </div>
          </div>

          <button
            className="inline-flex h-10 w-10 items-center justify-center border border-border bg-background sm:hidden"
            onClick={() => setMobileOpen((value) => !value)}
            aria-label="Toggle navigation"
          >
            {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>

        {mobileOpen && (
          <div className="border-t border-border bg-card px-4 py-3 sm:hidden">
            <div className="mb-3 border border-border bg-background px-3 py-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {connected ? 'api linked' : 'api missing'}
            </div>
            <div className="flex flex-col gap-2">
              {navItems.map(({ to, label, icon: Icon }) => {
                const active = location.pathname === to;
                return (
                  <Link
                    key={to}
                    to={to}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      'inline-flex items-center gap-2 border px-3 py-3 text-xs font-medium uppercase tracking-[0.18em]',
                      active
                        ? 'border-foreground bg-foreground text-background'
                        : 'border-border bg-background text-muted-foreground',
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </header>

      <main className="relative z-10 mx-auto w-full max-w-7xl px-4 py-8">{children}</main>

      <footer className="relative z-10 border-t border-border/80 bg-card/95">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            Local-first protocol browse surface
          </p>
          <p className="font-mono text-[11px] text-muted-foreground">
            Base URL: {API_BASE_URL || 'unset'}
          </p>
        </div>
      </footer>
    </div>
  );
}
