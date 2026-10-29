import { useState } from 'react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useBundle } from '@/data/useBundle'
import { cn } from '@/lib/utils'
import { LIME_BUTTON } from './page-surfaces'

const FIELD =
  'h-11 w-full rounded-lg border border-border bg-card px-3 text-[15px] text-foreground outline-none focus-visible:border-[var(--green,#285C35)] focus-visible:ring-2 focus-visible:ring-[var(--green,#285C35)]/30'

export function LoginPage() {
  const { bundle, hall, setHall } = useBundle()
  const navigate = useNavigate()
  const [pick, setPick] = useState(hall)

  const signIn = (e: React.FormEvent) => {
    e.preventDefault()
    setHall(pick)
    navigate('/dashboard')
  }

  return (
    <main className="grid min-h-dvh place-items-center bg-[var(--bg,#FAFBF9)] px-4 py-10">
      <div className="w-full max-w-[400px]">
        <p className="mb-8 text-center font-heading text-[22px] font-semibold tracking-tight text-foreground">
          Second Serve
        </p>

        <form onSubmit={signIn} className="rounded-xl border border-border bg-card p-6">
          <h1 className="font-heading text-[24px] leading-tight font-semibold text-foreground">Sign in</h1>
          <p className="mt-1 mb-6 text-[14px] text-muted-foreground">Use any credentials. This is a prototype.</p>

          <div className="space-y-4">
            <div>
              <Label htmlFor="login-email" className="mb-1.5 text-[14px] text-foreground">
                Email
              </Label>
              <input id="login-email" type="email" className={FIELD} defaultValue="dining.team@example.edu" />
            </div>
            <div>
              <Label htmlFor="login-password" className="mb-1.5 text-[14px] text-foreground">
                Password
              </Label>
              <input id="login-password" type="password" className={FIELD} defaultValue="secondserve" />
            </div>
            <div>
              <Label htmlFor="hall-pick" className="mb-1.5 text-[14px] text-foreground">
                Dining hall
              </Label>
              <Select value={pick} onValueChange={setPick}>
                <SelectTrigger id="hall-pick" className="h-11! w-full rounded-lg text-[15px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {bundle.halls.map((h) => (
                    <SelectItem key={h.id} value={h.id} className="min-h-11">
                      {h.name}
                    </SelectItem>
                  ))}
                  <SelectItem value="all" className="min-h-11">
                    All dining halls
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button type="submit" className={cn(LIME_BUTTON, 'mt-6 w-full')}>
            Sign in
          </Button>
        </form>

        <p className="mt-4 text-center text-[13px] text-muted-foreground">Fictional scenario · Sample data only</p>
      </div>
    </main>
  )
}
