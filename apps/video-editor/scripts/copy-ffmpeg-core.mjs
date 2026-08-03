import { copyFileSync, mkdirSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = path.dirname(fileURLToPath(import.meta.url))
const src = path.join(root, '..', 'node_modules', '@ffmpeg', 'core', 'dist', 'esm')
const dest = path.join(root, '..', 'public', 'ffmpeg')

if (!existsSync(src)) {
  console.warn('[copy-ffmpeg-core] @ffmpeg/core not installed, skipping.')
  process.exit(0)
}

mkdirSync(dest, { recursive: true })
for (const file of ['ffmpeg-core.js', 'ffmpeg-core.wasm']) {
  copyFileSync(path.join(src, file), path.join(dest, file))
}
console.log('[copy-ffmpeg-core] copied ffmpeg-core assets to public/ffmpeg/')
