/** A labelled value. Every number in the walkthrough renders through a label like this. */
export function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">{label}</dt>
      <dd className="tabular text-[13.5px] break-words">{children}</dd>
    </div>
  )
}
