import { useState } from 'react'
import { cn } from '@/lib/utils'

// Categorical slots validated with the dataviz validator against #fff (amber < 3:1, so every chart
// ships a legend, hover values and a screen-reader table).
export const SERIES = {
  expired: '#b5533a',
  kitchen: '#d9963f',
  plate: '#7a64d6',
  onsite: '#2d8c62',
  transfer: '#d9963f',
  recover: '#7a64d6',
} as const

const GRID = '#eef2ef'
const AXIS_TEXT = '#8a9891'

export interface Segment {
  key: string
  label: string
  color: string
}

export function Legend({ items }: { items: Segment[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {items.map((s) => (
        <span key={s.key} className="inline-flex items-center gap-1.5">
          <i className="inline-block size-2 rounded-full" style={{ background: s.color }} />
          {s.label}
        </span>
      ))}
    </div>
  )
}

function niceMax(v: number) {
  if (v <= 0) return 10
  const p = 10 ** Math.floor(Math.log10(v))
  const n = v / p
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p
}

function Tip({ x, y, children }: { x: number; y: number; children: React.ReactNode }) {
  return (
    <div
      className="pointer-events-none absolute z-10 min-w-36 -translate-x-1/2 -translate-y-full rounded-lg bg-ink px-3 py-2 text-xs text-white shadow-lg"
      style={{ left: `${x}%`, top: `${y}%` }}
    >
      {children}
    </div>
  )
}

/** Stacked daily bars. Columns after `splitIndex` render as projections. */
export function StackedBars({
  rows,
  segments,
  splitIndex,
  unit = 'lb',
  title,
}: {
  rows: { label: string; sub?: string; values: Record<string, number> }[]
  segments: Segment[]
  splitIndex?: number
  unit?: string
  title: string
}) {
  const [hover, setHover] = useState<number | null>(null)
  const W = 420
  const H = 170
  const top = 10
  const left = 34
  const bottom = 22
  const plotH = H - top - bottom
  const totals = rows.map((r) => segments.reduce((a, s) => a + (r.values[s.key] ?? 0), 0))
  const max = niceMax(Math.max(...totals, 1))
  const colW = (W - left - 6) / rows.length
  const barW = Math.min(26, colW * 0.5)
  const ticks = [0, 0.5, 1].map((t) => t * max)

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={title}>
        {ticks.map((t) => {
          const y = top + plotH - (t / max) * plotH
          return (
            <g key={t}>
              <line x1={left} x2={W} y1={y} y2={y} stroke={GRID} />
              <text x={left - 6} y={y + 3} fontSize="9" fill={AXIS_TEXT} textAnchor="end">
                {Math.round(t)}
              </text>
            </g>
          )
        })}
        {rows.map((r, i) => {
          const cx = left + colW * i + colW / 2
          const projected = splitIndex !== undefined && i > splitIndex
          let y = top + plotH
          const parts = segments.map((s) => ({ s, v: r.values[s.key] ?? 0 })).filter((p) => p.v > 0)
          return (
            <g key={r.label} opacity={projected ? 0.42 : 1}>
              {parts.map((p, j) => {
                const h = Math.max(0, (p.v / max) * plotH - (j < parts.length - 1 ? 2 : 0))
                y -= (p.v / max) * plotH
                const isTop = j === parts.length - 1
                return isTop ? (
                  <path
                    key={p.s.key}
                    d={`M${cx - barW / 2},${y + h} v${-(h - 4)} a4,4 0 0 1 4,-4 h${barW - 8} a4,4 0 0 1 4,4 v${h - 4} z`}
                    fill={p.s.color}
                  />
                ) : (
                  <rect key={p.s.key} x={cx - barW / 2} y={y + 2} width={barW} height={h} fill={p.s.color} />
                )
              })}
              <text
                x={cx}
                y={H - 6}
                fontSize="10"
                fill={i === splitIndex ? '#1b2a24' : AXIS_TEXT}
                fontWeight={i === splitIndex ? 700 : 400}
                textAnchor="middle"
              >
                {r.label}
              </text>
              {/* biome-ignore lint/a11y/noStaticElementInteractions: hover/focus target that only reveals the tooltip; data is also in the sr-only table */}
              <rect
                x={cx - colW / 2}
                y={top}
                width={colW}
                height={plotH}
                fill="transparent"
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                tabIndex={0}
                aria-label={`${r.label}: ${Math.round(totals[i])} ${unit}`}
              />
            </g>
          )
        })}
      </svg>
      {hover !== null ? (
        <Tip
          x={((left + colW * hover + colW / 2) / W) * 100}
          y={((top + plotH - (totals[hover] / max) * plotH) / H) * 100}
        >
          <div className="mb-1 font-semibold">
            {rows[hover].sub ?? rows[hover].label}
            {splitIndex !== undefined && hover > splitIndex ? ' · projected' : ''}
          </div>
          {segments.map((s) => (
            <div key={s.key} className="flex items-center justify-between gap-3">
              <span className="inline-flex items-center gap-1.5">
                <i className="inline-block size-2 rounded-full" style={{ background: s.color }} />
                {s.label}
              </span>
              <span className="tabular">{(rows[hover].values[s.key] ?? 0).toFixed(1)}</span>
            </div>
          ))}
          <div className="mt-1 flex justify-between border-t border-white/20 pt-1 font-semibold">
            <span>Total</span>
            <span className="tabular">
              {totals[hover].toFixed(1)} {unit}
            </span>
          </div>
        </Tip>
      ) : null}
      <DataTable title={title} rows={rows} segments={segments} />
    </div>
  )
}

function DataTable({
  title,
  rows,
  segments,
}: {
  title: string
  rows: { label: string; values: Record<string, number> }[]
  segments: Segment[]
}) {
  return (
    <div className="sr-only">
      <table>
        <caption>{title}</caption>
        <thead>
          <tr>
            <th>Row</th>
            {segments.map((s) => (
              <th key={s.key}>{s.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label}>
              <td>{r.label}</td>
              {segments.map((s) => (
                <td key={s.key}>{(r.values[s.key] ?? 0).toFixed(1)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Single-series line with crosshair hover. */
export function TrendLine({
  points,
  unit = 'lb',
  title,
  color = '#285C35', // Why: SVG attributes don't resolve var(); literal --green from docs/design-spec.md.
}: {
  points: { label: string; sub?: string; value: number }[]
  unit?: string
  title: string
  color?: string
}) {
  const [hover, setHover] = useState<number | null>(null)
  const W = 420
  const H = 170
  const top = 12
  const left = 34
  const right = 14
  const bottom = 22
  const plotH = H - top - bottom
  const max = niceMax(Math.max(...points.map((p) => p.value), 1))
  const step = (W - left - right) / Math.max(points.length - 1, 1)
  const xy = points.map((p, i) => [left + i * step, top + plotH - (p.value / max) * plotH] as const)
  const line = xy.map(([x, y]) => `${x},${y}`).join(' ')
  const area = `M${left},${top + plotH} L${line.replaceAll(' ', ' L')} L${left + (points.length - 1) * step},${top + plotH} Z`

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={title}>
        <defs>
          <linearGradient id="trend-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor={color} stopOpacity="0.16" />
            <stop offset="1" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 0.5, 1].map((t) => {
          const y = top + plotH - t * plotH
          return (
            <g key={t}>
              <line x1={left} x2={W - right} y1={y} y2={y} stroke={GRID} />
              <text x={left - 6} y={y + 3} fontSize="9" fill={AXIS_TEXT} textAnchor="end">
                {Math.round(t * max)}
              </text>
            </g>
          )
        })}
        <path d={area} fill="url(#trend-fill)" />
        <polyline points={line} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
        {hover !== null ? (
          <line x1={xy[hover][0]} x2={xy[hover][0]} y1={top} y2={top + plotH} stroke="#c9d4ce" strokeDasharray="3 3" />
        ) : null}
        {xy.map(([x, y], i) => (
          <g key={points[i].label}>
            <circle cx={x} cy={y} r={hover === i ? 5 : 4} fill={color} stroke="#fff" strokeWidth="2" />
            <text x={x} y={H - 6} fontSize="9.5" fill={AXIS_TEXT} textAnchor="middle">
              {points[i].label}
            </text>
            {/* biome-ignore lint/a11y/noStaticElementInteractions: hover/focus target that only reveals the tooltip; data is also in the sr-only table */}
            <rect
              x={x - step / 2}
              y={top}
              width={step}
              height={plotH}
              fill="transparent"
              tabIndex={0}
              aria-label={`${points[i].label}: ${points[i].value.toFixed(1)} ${unit}`}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(i)}
              onBlur={() => setHover(null)}
            />
          </g>
        ))}
      </svg>
      {hover !== null ? (
        <Tip x={(xy[hover][0] / W) * 100} y={(xy[hover][1] / H) * 100 - 3}>
          <div className="font-semibold">{points[hover].sub ?? points[hover].label}</div>
          <div className="tabular">
            {points[hover].value.toFixed(1)} {unit}
          </div>
        </Tip>
      ) : null}
      <div className="sr-only">
        <table>
          <caption>{title}</caption>
          <tbody>
            {points.map((p) => (
              <tr key={p.label}>
                <td>{p.label}</td>
                <td>{p.value.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/** Horizontal stacked bars, one row per entity, total label at the end. */
export function HBars({
  rows,
  segments,
  title,
  unit = 'lb',
}: {
  rows: { label: string; values: Record<string, number> }[]
  segments: Segment[]
  title: string
  unit?: string
}) {
  const [hover, setHover] = useState<number | null>(null)
  const totals = rows.map((r) => segments.reduce((a, s) => a + (r.values[s.key] ?? 0), 0))
  const max = Math.max(...totals, 1)
  return (
    <div className="space-y-2.5" role="img" aria-label={title}>
      {rows.map((r, i) => (
        // biome-ignore lint/a11y/noStaticElementInteractions: hover only reveals the tooltip; data is also in the sr-only table
        <div
          key={r.label}
          className="relative grid grid-cols-[84px_1fr] items-center gap-2.5"
          onMouseEnter={() => setHover(i)}
          onMouseLeave={() => setHover(null)}
        >
          <span className="truncate text-right text-xs">{r.label}</span>
          <div className="flex items-center gap-2">
            <div className="flex h-[18px] gap-[2px]" style={{ width: `${(totals[i] / max) * 78}%` }}>
              {segments.map((s, j) => {
                const v = r.values[s.key] ?? 0
                if (!v) return null
                const last = segments.slice(j + 1).every((n) => !(r.values[n.key] ?? 0))
                return (
                  <div
                    key={s.key}
                    className={cn('h-full', j === 0 && 'rounded-l-[4px]', last && 'rounded-r-[4px]')}
                    style={{ flexGrow: v, background: s.color }}
                  />
                )
              })}
            </div>
            <span className="tabular whitespace-nowrap text-xs text-muted-foreground">
              {totals[i].toFixed(0)} {unit}
            </span>
          </div>
          {hover === i ? (
            <div className="pointer-events-none absolute top-0 left-[92px] z-10 -translate-y-full rounded-lg bg-ink px-3 py-2 text-xs text-white shadow-lg">
              {segments.map((s) => (
                <div key={s.key} className="flex justify-between gap-3">
                  <span>{s.label}</span>
                  <span className="tabular">{(r.values[s.key] ?? 0).toFixed(1)}</span>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ))}
      <DataTable title={title} rows={rows} segments={segments} />
    </div>
  )
}
