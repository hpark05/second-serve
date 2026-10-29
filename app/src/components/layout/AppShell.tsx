import { CalendarDays, Home, LogOut, Network, Package, PlayCircle, Sparkles, TrendingUp } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { Link, NavLink, Outlet, useLocation, useSearchParams } from 'react-router'
import { useBundle } from '@/data/useBundle'
import { cn } from '@/lib/utils'
import { RoleSwitcher } from '@/walkthrough/RoleSwitcher'
import { type Seat, seatHall } from '@/walkthrough/roles'
import { useScenarioContext } from '@/walkthrough/useScenario'
import { AppHeader } from './AppHeader'
import { StageSegments, StageSidebar } from './WalkthroughStageNav'
import { walkthroughPosition } from './walkthrough-progress'

const NAV = [
  { to: '/walkthrough/1', label: 'Sample transfer', icon: PlayCircle },
  { to: '/dashboard', label: 'Dashboard', icon: Home },
  { to: '/inventory', label: 'Inventory', icon: Package },
  { to: '/recommendations', label: 'AI Recommendations', icon: Sparkles },
  { to: '/campus', label: 'Campus Network', icon: Network },
  { to: '/meal-planning', label: 'Meal Planning', icon: CalendarDays },
  { to: '/impact', label: 'Impact', icon: TrendingUp },
]

const navClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    'flex min-h-11 flex-none items-center gap-2.5 rounded-control px-3 text-label whitespace-nowrap transition-colors',
    isActive ? 'bg-lime-soft font-semibold text-ink' : 'text-muted-foreground hover:bg-muted hover:text-ink',
  )

/** Presenter mode (`/present` or `?autoplay=1`) hides all chrome so the page fills the screen. */
export function useChromeless() {
  const { pathname } = useLocation()
  const [params] = useSearchParams()
  return pathname === '/present' || pathname.startsWith('/present/') || params.get('autoplay') === '1'
}

function PageTransition({ children, routeKey }: { children: React.ReactNode; routeKey: string }) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={routeKey}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2, ease: 'easeOut' }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}

export function AppShell() {
  const { setHall, isFixture, bundle } = useBundle()
  const { seat, setSeat, load } = useScenarioContext()
  const location = useLocation()
  const chromeless = useChromeless()
  const walkthrough = location.pathname.startsWith('/walkthrough')
  const sample = load.status === 'ready' ? load.scenario : null
  const pos = walkthroughPosition(location.pathname)

  if (chromeless) {
    return (
      <main className="min-h-dvh bg-background">
        <Outlet />
      </main>
    )
  }

  const onSeat = (s: Seat) => {
    setSeat(s)
    if (sample) setHall(seatHall(s, sample.kitchens.a.hall_id, sample.kitchens.b.hall_id))
  }

  // Why: spec puts role changes inside the walkthrough on guided handoff cards; the header switcher is free-roam only.
  const roleSlot = walkthrough ? null : <RoleSwitcher seat={seat} onSeat={onSeat} />

  return (
    <div className="flex min-h-dvh flex-col">
      <AppHeader walkthrough={walkthrough} roleSlot={roleSlot} bannerLabel={sample?.banner_label} />

      <div className="flex-1 lg:grid lg:grid-cols-[272px_minmax(0,1fr)]">
        <aside className="no-print hidden border-r bg-card lg:block">
          <div className="sticky top-16 flex max-h-[calc(100dvh-4rem)] flex-col gap-6 overflow-y-auto px-3 py-6">
            {walkthrough ? (
              <StageSidebar pos={pos} />
            ) : (
              <nav aria-label="Main" className="flex flex-col gap-0.5">
                {NAV.map(({ to, label, icon: Icon }) => (
                  <NavLink key={to} to={to} className={navClass}>
                    <Icon className="size-4" aria-hidden="true" />
                    {label}
                  </NavLink>
                ))}
              </nav>
            )}
            <div className="mt-auto flex flex-col gap-0.5 border-t pt-4">
              {walkthrough ? (
                <NavLink to="/dashboard" className={navClass} end>
                  Exit walkthrough
                </NavLink>
              ) : null}
              <Link to="/" className={navClass({ isActive: false })}>
                <LogOut className="size-4" aria-hidden="true" />
                Sign out
              </Link>
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-col">
          {/* Under 1024px the sidebar collapses to a top bar: stage segments on the walkthrough, main nav elsewhere. */}
          <div className="no-print border-b bg-card px-4 py-3 sm:px-6 lg:hidden">
            {walkthrough ? (
              <StageSegments pos={pos} />
            ) : (
              <nav aria-label="Main" className="-mx-1 flex gap-1 overflow-x-auto px-1">
                {NAV.map(({ to, label, icon: Icon }) => (
                  <NavLink key={to} to={to} className={navClass}>
                    <Icon className="size-4" aria-hidden="true" />
                    {label}
                  </NavLink>
                ))}
              </nav>
            )}
          </div>

          <main
            className={cn(
              'mx-auto w-full min-w-0 flex-1 px-4 pt-6 pb-12 sm:px-6',
              walkthrough ? 'max-w-[960px]' : 'max-w-[1100px]',
            )}
          >
            <PageTransition routeKey={location.pathname}>
              <Outlet />
            </PageTransition>
          </main>

          <footer className="no-print flex flex-wrap items-center justify-between gap-2 border-t px-4 py-3 text-meta text-muted-foreground sm:px-6">
            <span>Second Serve · prototype for Cal Dining · {isFixture ? 'fixture' : bundle.meta.scenario} bundle</span>
            <Link to="/sources" className="inline-flex min-h-11 items-center font-medium text-green hover:underline">
              How we built the numbers
            </Link>
          </footer>
        </div>
      </div>
    </div>
  )
}
