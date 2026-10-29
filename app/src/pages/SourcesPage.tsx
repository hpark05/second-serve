import { ExternalLink } from 'lucide-react'
import { useEffect } from 'react'
import { useLocation } from 'react-router'
import { useBundle } from '@/data/useBundle'
import { cn } from '@/lib/utils'
import sources from '../../../docs/sources.json'
import { Chip, PageTitle, Surface, SurfaceTitle } from './page-surfaces'

interface Source {
  id: string
  title: string
  org: string
  year: number
  url: string
  used_for: string
  confidence: 'high' | 'med' | 'low' | string
}

interface FactorSource {
  value: number
  basis: string
  source_url: string
}

const CONFIDENCE: Record<string, { label: string; tone: 'verified' | 'planned' | 'declined' }> = {
  high: { label: 'High', tone: 'verified' },
  med: { label: 'Medium', tone: 'planned' },
  low: { label: 'Low', tone: 'declined' },
}

const TARGET = 'bg-[var(--lime-soft,#EAF8E2)]'

export function SourcesPage() {
  const { bundle } = useBundle()
  const { hash } = useLocation()
  const target = decodeURIComponent(hash.slice(1))
  // Why: react-router does not scroll to #fragments; Illustrative chips deep-link to one source row.
  useEffect(() => {
    if (target) document.getElementById(target)?.scrollIntoView({ block: 'center' })
  }, [target])

  const factorSources = (bundle.meta as unknown as { factor_sources?: Record<string, FactorSource> }).factor_sources
  const list = sources as Source[]

  return (
    <div className="max-w-[960px]">
      <PageTitle
        title="Sources"
        sub="Cal Dining has shared no internal data. Every figure in Second Serve is synthetic or illustrative and traces to a public source below."
      />

      {factorSources ? (
        <Surface className="mb-6">
          <SurfaceTitle title="Conversion factors" hint="Used by Impact and recommendation savings" />
          <dl className="divide-y divide-border">
            {Object.entries(factorSources).map(([k, f]) => (
              <div
                key={k}
                id={k}
                className={cn(
                  'scroll-mt-24 grid gap-1 rounded-lg px-3 py-3 sm:grid-cols-[220px_1fr]',
                  target === k && TARGET,
                )}
              >
                <dt className="font-medium text-foreground">
                  <code className="text-[13px]">{k}</code> ={' '}
                  <span className="tabular">{Number(f.value.toFixed(3))}</span>
                </dt>
                <dd className="text-[14px] text-muted-foreground">
                  {f.basis}{' '}
                  {f.source_url.startsWith('http') ? (
                    <a
                      href={f.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex min-h-11 items-center font-medium text-[var(--green,#285C35)] underline-offset-4 hover:underline"
                    >
                      Source
                    </a>
                  ) : (
                    <code className="text-[12px] break-all">{f.source_url}</code>
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </Surface>
      ) : null}

      <Surface id="ingredient_prices" className={cn('mb-6 scroll-mt-24', target === 'ingredient_prices' && TARGET)}>
        <SurfaceTitle
          title="Ingredient prices"
          hint="Every dollar figure uses these wholesale prices, not Cal Dining purchase data"
        />
        <p className="text-[14px] leading-relaxed text-foreground">
          USD per as-purchased pound for each ingredient, in late-2026 dollars, with a low, mid and high price. Headline
          savings use the mid price and show the low to high range. The table is{' '}
          <code className="text-[13px] break-all">data/raw/prices/ingredient_prices.csv</code>, built from public
          wholesale reports. Each quote and its source is listed in{' '}
          <code className="text-[13px] break-all">docs/sources-prices.md</code>.
        </p>
      </Surface>

      <Surface className="p-0">
        <div className="p-6 pb-2">
          <SurfaceTitle title="Public sources" hint={`${list.length} sources`} />
        </div>
        {/* Table at 768+; each row stacks into a block below so nothing scrolls sideways. */}
        <table className="w-full text-left text-[14px] max-md:block">
          <thead className="border-y border-border text-[13px] text-muted-foreground max-md:hidden">
            <tr>
              <th scope="col" className="px-6 py-3 font-medium">
                Source
              </th>
              <th scope="col" className="px-3 py-3 font-medium">
                Used for
              </th>
              <th scope="col" className="px-6 py-3 font-medium">
                Confidence
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border max-md:block max-md:border-t max-md:border-border">
            {list.map((s) => {
              const c = CONFIDENCE[s.confidence]
              return (
                <tr
                  key={s.id}
                  id={s.id}
                  className={cn(
                    'scroll-mt-24 align-top max-md:block max-md:px-6 max-md:py-4',
                    target === s.id && TARGET,
                  )}
                >
                  <td className="px-6 py-4 max-md:block max-md:p-0">
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex min-h-11 items-center gap-1.5 font-medium break-words text-foreground underline-offset-4 hover:underline"
                    >
                      {s.title}
                      <ExternalLink className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                    </a>
                    <p className="mt-0.5 text-[13px] text-muted-foreground">
                      {s.org}, {s.year} · <code className="text-[12px] break-all">{s.id}</code>
                    </p>
                  </td>
                  <td className="px-3 py-4 text-foreground max-md:block max-md:p-0 max-md:pt-2">{s.used_for}</td>
                  <td className="px-6 py-4 max-md:block max-md:p-0 max-md:pt-2">
                    <Chip tone={c?.tone}>{c?.label ?? s.confidence}</Chip>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </Surface>
    </div>
  )
}
