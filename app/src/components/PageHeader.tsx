export function PageHeader({
  title,
  sub,
  action,
}: {
  title: React.ReactNode
  sub?: React.ReactNode
  action?: React.ReactNode
}) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-[26px] leading-tight sm:text-[28px]">{title}</h1>
        {sub ? <p className="mt-1 text-[13.5px] text-muted-foreground">{sub}</p> : null}
      </div>
      {action ? <div className="flex flex-wrap items-center gap-2">{action}</div> : null}
    </div>
  )
}

export function Panel({ className = '', children }: { className?: string; children: React.ReactNode }) {
  return <div className={`rounded-[14px] border bg-card p-4 shadow-card ${className}`}>{children}</div>
}

export function PanelTitle({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="mb-3">
      <h3 className="text-[16px]">{title}</h3>
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  )
}

export function AgentNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-3.5 flex items-start gap-2.5 rounded-xl bg-green-soft px-3.5 py-3 text-[13px]">
      <span className="mt-px grid size-[22px] flex-none place-items-center rounded-[7px] bg-green">
        <svg viewBox="0 0 24 24" className="size-[14px]" fill="#fff" aria-hidden="true">
          <path d="M4 20c0-9 6-14 16-16-1 10-6 16-16 16zm0 0c3-5 7-8 12-10" />
        </svg>
      </span>
      <div>{children}</div>
    </div>
  )
}
