import { CheckCircle2, CircleDashed, XCircle } from 'lucide-react'
import { motion } from 'motion/react'
import { CHECK_LABEL } from './labels'
import { SIMULATED_IMPORT_LABEL } from './steps'
import { weekdayProse } from './ui/scenario-weekday'
import { useTransfer } from './useScenario'

/** The three checks that verify a transfer. Only a system import fills them; no button here. */
export function VerificationChecks() {
  const { verified, expectedChecks, imports, scenario } = useTransfer()
  const done = new Map((verified?.checks ?? []).map((c) => [c.check, c]))
  return (
    <section aria-label="Verification checks" className="rounded-xl border bg-card p-6">
      <h3 className="text-[18px] leading-snug">
        {verified?.status === 'verified' ? 'Verified by Eatec records' : 'Not yet verified'}
      </h3>
      <p className="mt-1 mb-4 text-[14px] text-muted-foreground">
        {imports.length
          ? `${SIMULATED_IMPORT_LABEL}. No one clicked verify.`
          : 'Turns verified only when the next Eatec export shows all three. Nobody can click verified.'}
      </p>
      <ol className="divide-y">
        {expectedChecks.map((c, i) => {
          const got = done.get(c.check)
          const status = got?.status ?? 'pending'
          const Icon = status === 'match' ? CheckCircle2 : status === 'mismatch' ? XCircle : CircleDashed
          return (
            <motion.li
              key={`${c.check}-${status}`}
              initial={status === 'pending' ? false : { opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: i * 0.6 }}
              className="flex items-start gap-3 py-3 text-[14px]"
            >
              <Icon
                className={
                  status === 'match'
                    ? 'mt-0.5 size-5 flex-none text-green'
                    : status === 'mismatch'
                      ? 'mt-0.5 size-5 flex-none text-red'
                      : 'mt-0.5 size-5 flex-none text-muted-foreground'
                }
                aria-hidden="true"
              />
              <div className="min-w-0">
                <p className="text-ink">
                  <span className="font-medium">{CHECK_LABEL[c.check].title}</span>
                  <span className="text-muted-foreground"> · {status === 'match' ? 'matched' : status}</span>
                </p>
                <p className="text-[13px] text-muted-foreground">
                  {got?.evidence ? weekdayProse(scenario, got.evidence) : CHECK_LABEL[c.check].source}
                </p>
              </div>
            </motion.li>
          )
        })}
      </ol>
    </section>
  )
}
