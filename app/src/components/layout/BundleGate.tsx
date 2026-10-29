import { Loader2 } from 'lucide-react'
import { Wordmark } from '@/components/brand/LeafMark'
import { useBundleContext } from '@/data/useBundle'

/** Renders children only once the bundle is loaded, so pages can call useBundle() unconditionally. */
export function BundleGate({ children }: { children: React.ReactNode }) {
  const { state } = useBundleContext()
  if (state.status === 'ready') return children
  return (
    <div className="grid min-h-dvh place-items-center p-6 text-center">
      <div>
        <Wordmark className="justify-center" />
        {state.status === 'loading' ? (
          <p className="mt-3 inline-flex items-center gap-2 text-muted-foreground">
            <Loader2 className="size-4 animate-spin" /> Loading data…
          </p>
        ) : (
          <p className="mt-3 max-w-sm text-red">Couldn't load data. {state.error}</p>
        )}
      </div>
    </div>
  )
}
