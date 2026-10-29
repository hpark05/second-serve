// GitHub Pages has no rewrites: serving index.html as 404.html lets deep links like /second-serve/inventory load the SPA.
import { copyFileSync } from 'node:fs'
import path from 'node:path'

const dist = path.join(import.meta.dirname, '..', 'dist')
copyFileSync(path.join(dist, 'index.html'), path.join(dist, '404.html'))
