// Copies generator output (../data/synthetic/<scenario>/bundle.json) into public/data/<scenario>/ so the app serves it.
import { copyFileSync, existsSync, mkdirSync } from 'node:fs'
import path from 'node:path'

const SCENARIOS = ['normal_week', 'game_day', 'finals_week', 'holiday_short_week']
const repo = path.join(import.meta.dirname, '..', '..')
let copied = 0
for (const s of SCENARIOS) {
  const src = path.join(repo, 'data', 'synthetic', s, 'bundle.json')
  if (!existsSync(src)) {
    console.log(`skip ${s}: no ${path.relative(repo, src)}`)
    continue
  }
  const dest = path.join(import.meta.dirname, '..', 'public', 'data', s, 'bundle.json')
  mkdirSync(path.dirname(dest), { recursive: true })
  copyFileSync(src, dest)
  // Why: Impact reads the generator's deduplicated savings range (low/mid/high) from summary.json.
  const summary = path.join(path.dirname(src), 'summary.json')
  if (existsSync(summary)) copyFileSync(summary, path.join(path.dirname(dest), 'summary.json'))
  copied++
  console.log(`copied ${s}`)
}
console.log(`${copied}/${SCENARIOS.length} scenario bundles synced; missing ones fall back to the fixture.`)
