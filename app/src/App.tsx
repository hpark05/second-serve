import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { AppShell } from '@/components/layout/AppShell'
import { BundleGate } from '@/components/layout/BundleGate'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { BundleProvider } from '@/data/useBundle'
import { LoginPage } from '@/pages/LoginPage'
import { ScenarioProvider } from '@/walkthrough/useScenario'

const CampusPage = lazy(() => import('@/pages/CampusPage').then((m) => ({ default: m.CampusPage })))
const DashboardPage = lazy(() => import('@/pages/DashboardPage').then((m) => ({ default: m.DashboardPage })))
const ImpactPage = lazy(() => import('@/pages/ImpactPage').then((m) => ({ default: m.ImpactPage })))
const InventoryPage = lazy(() => import('@/pages/InventoryPage').then((m) => ({ default: m.InventoryPage })))
const MealPlanningPage = lazy(() => import('@/pages/MealPlanningPage').then((m) => ({ default: m.MealPlanningPage })))
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage })))
const RecommendationsPage = lazy(() =>
  import('@/pages/RecommendationsPage').then((m) => ({ default: m.RecommendationsPage })),
)
const WalkthroughPage = lazy(() =>
  import('@/walkthrough/WalkthroughPage').then((m) => ({ default: m.WalkthroughPage })),
)
const PresenterPage = lazy(() => import('@/walkthrough/PresenterPage').then((m) => ({ default: m.PresenterPage })))
const SourcesPage = lazy(() => import('@/pages/SourcesPage').then((m) => ({ default: m.SourcesPage })))

// Why: BASE_URL is '/second-serve/' on GitHub Pages and '/' on Vercel; strip the trailing slash for the router.
const basename = import.meta.env.BASE_URL.replace(/\/$/, '') || '/'

export default function App() {
  return (
    <BundleProvider>
      <ScenarioProvider>
        <TooltipProvider>
          <BrowserRouter basename={basename}>
            <BundleGate>
              <Suspense fallback={null}>
                <Routes>
                  <Route index element={<LoginPage />} />
                  <Route path="login" element={<Navigate to="/" replace />} />
                  <Route element={<AppShell />}>
                    <Route path="dashboard" element={<DashboardPage />} />
                    <Route path="inventory" element={<InventoryPage />} />
                    <Route path="recommendations" element={<RecommendationsPage />} />
                    <Route path="campus" element={<CampusPage />} />
                    <Route path="meal-planning" element={<MealPlanningPage />} />
                    <Route path="impact" element={<ImpactPage />} />
                    <Route path="sources" element={<SourcesPage />} />
                    <Route path="walkthrough" element={<Navigate to="/walkthrough/1" replace />} />
                    <Route path="walkthrough/:step" element={<WalkthroughPage />} />
                    {/* AppShell renders chromeless on /present. */}
                    <Route path="present" element={<PresenterPage />} />
                    <Route path="*" element={<NotFoundPage />} />
                  </Route>
                </Routes>
              </Suspense>
            </BundleGate>
          </BrowserRouter>
          <Toaster />
        </TooltipProvider>
      </ScenarioProvider>
    </BundleProvider>
  )
}
