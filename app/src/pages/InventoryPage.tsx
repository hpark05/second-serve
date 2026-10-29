import { ArrowDown, ArrowUp, ArrowUpDown, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import {
  ALLOCATION_DAYS,
  allocationsOn,
  hallName,
  idx,
  inventoryOn,
  relDay,
  USE_FIRST_DAYS,
} from '@/data/bundle-selectors'
import { useBundle } from '@/data/useBundle'
import { cn } from '@/lib/utils'
import { weekdayAt, weekdayProse } from '@/walkthrough/ui/scenario-weekday'
import { useScenarioContext } from '@/walkthrough/useScenario'
import { Chip, LIME_BUTTON, Meta, PageTitle } from './page-surfaces'

type SortKey = 'name' | 'hall' | 'qty' | 'expiry'
type SortState = { key: SortKey; dir: 1 | -1 }

/** One display row; the pinned sample lot and bundle lots share it so table and stacked views stay identical. */
interface Row {
  key: string
  sample: boolean
  name: string
  lotLine: string
  hall: string
  onHand: string
  onHandNote?: string
  allocated: string
  allocatedNote?: string
  available: string
  useBy: string
  useByNote?: string
  updated: string
  source: string
  expiring: boolean
}

const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 1 })

function SortHead({
  k,
  sort,
  onSort,
  children,
  right,
}: {
  k: SortKey
  sort: SortState
  onSort: React.Dispatch<React.SetStateAction<SortState>>
  children: React.ReactNode
  right?: boolean
}) {
  const active = sort.key === k
  const Icon = active ? (sort.dir === 1 ? ArrowUp : ArrowDown) : ArrowUpDown
  return (
    <th
      scope="col"
      className={cn('px-2 font-medium', right && 'text-right')}
      aria-sort={active ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none'}
    >
      <button
        type="button"
        onClick={() => onSort((s) => ({ key: k, dir: s.key === k ? (s.dir === 1 ? -1 : 1) : 1 }))}
        className={cn(
          'inline-flex min-h-11 min-w-11 items-center gap-1',
          active ? 'text-foreground' : 'text-muted-foreground hover:text-foreground',
        )}
      >
        {children}
        <Icon className="size-3.5" aria-hidden="true" />
      </button>
    </th>
  )
}

export function InventoryPage() {
  const { bundle, hall } = useBundle()
  const { load } = useScenarioContext()
  const sample = load.status === 'ready' ? load.scenario : null
  const showSample = Boolean(sample && (hall === 'all' || hall === sample.lot.hall_id))
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('all')
  const [sort, setSort] = useState<SortState>({ key: 'expiry', dir: 1 })
  const today = bundle.meta.as_of
  const allHalls = hall === 'all'

  const lots = useMemo(() => {
    const ing = idx(bundle).ingredient
    const alloc = allocationsOn(bundle, today, hall)
    return inventoryOn(bundle, today, hall).map((l) => {
      const i = ing.get(l.ingredient_id)
      const allocated = alloc.get(l.lot_id) ?? 0
      return {
        l,
        allocated,
        name: i?.name ?? l.ingredient_id,
        category: i?.category ?? 'other',
        hall: hallName(bundle, l.hall_id),
      }
    })
  }, [bundle, today, hall])

  const categories = useMemo(() => ['all', ...[...new Set(lots.map((r) => r.category))].sort()], [lots])

  const rows: Row[] = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const cmp: Record<SortKey, (a: (typeof lots)[number], b: (typeof lots)[number]) => number> = {
      name: (a, b) => a.name.localeCompare(b.name),
      hall: (a, b) => a.hall.localeCompare(b.hall),
      qty: (a, b) => a.l.qty_lb - b.l.qty_lb,
      expiry: (a, b) => a.l.expiry_date.localeCompare(b.l.expiry_date),
    }
    return lots
      .filter((r) => (cat === 'all' || r.category === cat) && r.name.toLowerCase().includes(needle))
      .sort((a, b) => cmp[sort.key](a, b) * sort.dir || a.l.expiry_date.localeCompare(b.l.expiry_date))
      .map(({ l, allocated, name, hall: h }) => ({
        key: l.lot_id,
        sample: false,
        name,
        lotLine: `${l.lot_id} · received ${relDay(l.received_date, today).toLowerCase()}`,
        hall: h,
        onHand: `${fmt(l.qty)} ${l.unit}`,
        onHandNote: l.unit !== 'lb' ? `${l.qty_lb.toFixed(1)} lb` : undefined,
        allocated: `${allocated.toFixed(1)} lb`,
        available: `${Math.max(0, l.qty_lb - allocated).toFixed(1)} lb`,
        useBy: relDay(l.expiry_date, today),
        useByNote: `${l.days_to_expiry} day${l.days_to_expiry === 1 ? '' : 's'} left`,
        updated: 'Today',
        source: 'Synthetic bundle',
        expiring: l.days_to_expiry <= USE_FIRST_DAYS,
      }))
  }, [lots, q, cat, sort, today])

  const pinned: Row | null =
    showSample && sample
      ? {
          key: sample.lot.lot_id,
          sample: true,
          name: sample.lot.ingredient_name,
          lotLine: `${sample.lot.lot_id} · received ${weekdayAt(sample, sample.lot.received)}`,
          hall: sample.kitchens.a.name,
          onHand: `${sample.lot.on_hand_lb} lb`,
          allocated: `${sample.lot.allocated.reduce((a, x) => a + x.qty_lb, 0)} lb`,
          allocatedNote: sample.lot.allocated.map((x) => x.menu_item.name).join(', '),
          available: `${sample.lot.available_lb} lb`,
          useBy: weekdayAt(sample, sample.lot.use_by),
          updated: weekdayAt(sample, sample.lot.exported_at),
          source: weekdayProse(sample, sample.lot.source_label),
          expiring: false,
        }
      : null

  const all = pinned ? [pinned, ...rows] : rows
  const expiringCount = lots.filter((r) => r.l.days_to_expiry <= USE_FIRST_DAYS).length

  return (
    <>
      <PageTitle
        title="Inventory"
        sub={`Stock on hand today. ${expiringCount} lot${expiringCount === 1 ? '' : 's'} expire within ${USE_FIRST_DAYS} days. Allocated is forecast production for the next ${ALLOCATION_DAYS} days.`}
        action={
          showSample ? (
            <Button asChild className={LIME_BUTTON}>
              <Link to="/walkthrough/1">Start sample transfer</Link>
            </Button>
          ) : null
        }
      />

      <div className="mb-4 flex flex-col gap-3">
        <label className="flex h-12 items-center gap-2 rounded-lg border border-border bg-card px-3 text-muted-foreground focus-within:border-[var(--green,#285C35)] focus-within:ring-2 focus-within:ring-[var(--green,#285C35)]/30">
          <Search className="size-4" aria-hidden="true" />
          <span className="sr-only">Search ingredients</span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search ingredients"
            className="h-11 min-w-0 flex-1 bg-transparent text-[15px] text-foreground outline-none"
          />
        </label>
        <fieldset className="flex flex-wrap gap-2">
          <legend className="sr-only">Category</legend>
          {categories.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCat(c)}
              aria-pressed={cat === c}
              className={cn(
                'h-11 rounded-full border px-4 text-[14px] capitalize transition-colors',
                cat === c
                  ? 'border-foreground bg-foreground text-card'
                  : 'border-border bg-card text-muted-foreground hover:text-foreground',
              )}
            >
              {c}
            </button>
          ))}
        </fieldset>
      </div>

      {/* Table at 1024+; stacked rows below so nothing scrolls sideways. */}
      <div className="hidden overflow-hidden rounded-xl border border-border bg-card lg:block">
        <table className="w-full table-fixed text-[14px]">
          {/* Why: fixed widths keep 7-8 columns inside the ~700px content area at 1024 without sideways scroll. */}
          <colgroup>
            <col />
            {allHalls ? <col className="w-[14%]" /> : null}
            <col className="w-[9%]" />
            <col className="w-[11%]" />
            <col className="w-[9%]" />
            <col className="w-[12%]" />
            <col className="w-[10%]" />
            <col className="w-[12%]" />
          </colgroup>
          <thead className="border-b border-border text-left text-[13px]">
            <tr>
              <SortHead sort={sort} onSort={setSort} k="name">
                Item
              </SortHead>
              {allHalls ? (
                <SortHead sort={sort} onSort={setSort} k="hall">
                  Hall
                </SortHead>
              ) : null}
              <SortHead sort={sort} onSort={setSort} k="qty" right>
                On hand
              </SortHead>
              <th scope="col" className="px-2 text-right font-medium text-muted-foreground">
                Allocated
              </th>
              <th scope="col" className="px-2 text-right font-medium text-muted-foreground">
                Available
              </th>
              <SortHead sort={sort} onSort={setSort} k="expiry">
                Use by
              </SortHead>
              <th scope="col" className="px-2 font-medium text-muted-foreground">
                Last updated
              </th>
              <th scope="col" className="px-2 font-medium text-muted-foreground">
                Source
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {all.map((r) => (
              <tr key={r.key} className={cn('align-top', r.sample && 'bg-[var(--lime-soft,#EAF8E2)]/50')}>
                <td className="px-2 py-3">
                  <span className="block font-medium break-words text-foreground">{r.name}</span>
                  <span className="mt-0.5 block text-[12px] break-words text-muted-foreground">{r.lotLine}</span>
                  {r.sample ? (
                    <Chip tone="sample" className="mt-1.5">
                      Sample data
                    </Chip>
                  ) : null}
                </td>
                {allHalls ? <td className="px-2 py-3">{r.hall}</td> : null}
                <td className="tabular px-2 py-3 text-right">
                  {r.onHand}
                  {r.onHandNote ? (
                    <span className="block text-[12px] text-muted-foreground">{r.onHandNote}</span>
                  ) : null}
                </td>
                <td className="tabular px-2 py-3 text-right">
                  {r.allocated}
                  {r.allocatedNote ? (
                    <span className="block text-[12px] text-muted-foreground">{r.allocatedNote}</span>
                  ) : null}
                </td>
                <td className="tabular px-2 py-3 text-right font-semibold text-foreground">{r.available}</td>
                <td className="tabular px-2 py-3">
                  {r.useBy}
                  {r.useByNote ? <span className="block text-[12px] text-muted-foreground">{r.useByNote}</span> : null}
                  {r.expiring ? (
                    <Chip tone="expiring" className="mt-1.5">
                      Expiring
                    </Chip>
                  ) : null}
                </td>
                <td className="tabular px-2 py-3">{r.updated}</td>
                <td className="px-2 py-3 text-[13px] text-muted-foreground">{r.source}</td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={allHalls ? 8 : 7} className="px-2 py-8 text-center text-muted-foreground">
                  No items match.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <ul className="space-y-3 lg:hidden">
        {all.map((r) => (
          <li
            key={r.key}
            className={cn(
              'rounded-xl border border-border bg-card p-4',
              r.sample && 'bg-[var(--lime-soft,#EAF8E2)]/50',
            )}
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="font-medium break-words text-foreground">{r.name}</p>
                <p className="mt-0.5 text-[12px] break-words text-muted-foreground">
                  {r.lotLine}
                  {allHalls ? ` · ${r.hall}` : ''}
                </p>
              </div>
              {r.sample ? (
                <Chip tone="sample">Sample data</Chip>
              ) : r.expiring ? (
                <Chip tone="expiring">Expiring</Chip>
              ) : null}
            </div>
            <dl className="mt-3 grid grid-cols-3 gap-3">
              <Meta label="On hand">{r.onHand}</Meta>
              <Meta label="Allocated">{r.allocated}</Meta>
              <Meta label="Available">
                <span className="font-semibold">{r.available}</span>
              </Meta>
              <Meta label="Use by">{r.useBy}</Meta>
              <Meta label="Updated">{r.updated}</Meta>
              <Meta label="Source" className="break-words">
                {r.source}
              </Meta>
            </dl>
          </li>
        ))}
        {rows.length === 0 ? <li className="py-8 text-center text-muted-foreground">No items match.</li> : null}
      </ul>
    </>
  )
}
