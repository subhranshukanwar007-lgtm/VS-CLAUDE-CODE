import { FFmpeg } from '@ffmpeg/ffmpeg'
import { toBlobURL } from '@ffmpeg/util'

// Served locally from public/ffmpeg/ (copied from node_modules by scripts/copy-ffmpeg-core.mjs
// on install) so the app works fully offline and isn't dependent on a CDN at runtime.
const CORE_BASE = `${import.meta.env.BASE_URL}ffmpeg`

let ffmpegPromise: Promise<FFmpeg> | null = null

/** Loads (once) and returns the shared FFmpeg (wasm) instance. */
export function getFFmpeg(onLog?: (message: string) => void): Promise<FFmpeg> {
  if (!ffmpegPromise) {
    ffmpegPromise = (async () => {
      const ffmpeg = new FFmpeg()
      if (onLog) {
        ffmpeg.on('log', ({ message }) => onLog(message))
      }
      await ffmpeg.load({
        coreURL: await toBlobURL(`${CORE_BASE}/ffmpeg-core.js`, 'text/javascript'),
        wasmURL: await toBlobURL(`${CORE_BASE}/ffmpeg-core.wasm`, 'application/wasm'),
      })
      return ffmpeg
    })()
  }
  return ffmpegPromise
}
