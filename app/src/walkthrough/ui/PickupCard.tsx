import { Clock, Package, Thermometer, User, UserCog } from 'lucide-react'
import type { ReactNode } from 'react'
import type { PickupDetails } from '@/data/scenario'
import { useTransfer } from '../useScenario'
import { weekdayWindow } from './scenario-weekday'

function Row({ icon: Icon, label, children }: { icon: typeof Clock; label: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-3">
      <Icon className="mt-0.5 size-5 flex-none text-muted-foreground" aria-hidden="true" />
      <div className="min-w-0">
        <dt className="text-[13px] text-muted-foreground">{label}</dt>
        <dd className="text-[16px] text-ink">{children}</dd>
      </div>
    </div>
  )
}

/** Pickup window, runner, carrier, cold-holding line and the coordinator who set it. */
export function PickupCard({ pickup }: { pickup: PickupDetails }) {
  const { scenario } = useTransfer()
  const coordinator = scenario.roles.find((r) => r.role === 'coordinator')
  return (
    <dl className="divide-y">
      <Row icon={Clock} label="Pickup window">
        {weekdayWindow(scenario, pickup.window)}
      </Row>
      <Row icon={User} label="Runner">
        {pickup.runner_role}
      </Row>
      <Row icon={Package} label="Carrier">
        {pickup.carrier}
      </Row>
      <Row icon={Thermometer} label="Keep cold">
        {scenario.temperature_constraint.hold_max_f}°F or colder
      </Row>
      {coordinator ? (
        <Row icon={UserCog} label="Coordinator">
          {coordinator.display_name}
        </Row>
      ) : null}
    </dl>
  )
}
