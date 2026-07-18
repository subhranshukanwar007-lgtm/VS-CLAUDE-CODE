import { fetchFile } from '@ffmpeg/util'
import type { FFmpeg } from '@ffmpeg/ffmpeg'
import { getFFmpeg } from './ffmpeg'
import type { Clip } from '../types'

const WIDTH = 1280
const HEIGHT = 720

// ffmpeg-core.wasm ships without fontconfig or system fonts, so drawtext needs an
// explicit fontfile or it refuses to render text at all.
let fontLoadPromise: Promise<void> | null = null
function ensureFontLoaded(ffmpeg: FFmpeg): Promise<void> {
  if (!fontLoadPromise) {
    fontLoadPromise = (async () => {
      const data = await fetchFile(`${import.meta.env.BASE_URL}fonts/DejaVuSans.ttf`)
      await ffmpeg.writeFile('font.ttf', data)
    })()
  }
  return fontLoadPromise
}

/** Escapes text for safe use inside an ffmpeg drawtext filter argument. */
function escapeDrawtext(text: string): string {
  return text
    .replace(/\\/g, '\\\\')
    .replace(/:/g, '\\:')
    .replace(/'/g, '’')
    .replace(/%/g, '\\%')
}

function textYExpr(position: Clip['textPosition']): string {
  switch (position) {
    case 'top':
      return '40'
    case 'bottom':
      return 'h-text_h-40'
    default:
      return '(h-text_h)/2'
  }
}

/** Detects whether a written input file has an audio stream, via ffprobe. */
async function probeHasAudio(ffmpeg: FFmpeg, filename: string): Promise<boolean> {
  try {
    await ffmpeg.ffprobe([
      '-v',
      'error',
      '-select_streams',
      'a',
      '-show_entries',
      'stream=index',
      '-of',
      'csv=p=0',
      filename,
      '-o',
      'probe_out.txt',
    ])
    const data = await ffmpeg.readFile('probe_out.txt')
    await ffmpeg.deleteFile('probe_out.txt')
    return new TextDecoder().decode(data as Uint8Array).trim().length > 0
  } catch {
    return false
  }
}

function buildFilterComplex(clips: Clip[], hasAudio: boolean[]): { filter: string; inputArgs: string[] } {
  const parts: string[] = []
  const inputArgs: string[] = []

  clips.forEach((clip, i) => {
    inputArgs.push('-i', `input${i}.mp4`)

    const speed = Math.min(2, Math.max(0.5, clip.speed))
    const outDuration = Math.max(0.05, (clip.trimEnd - clip.trimStart) / speed)

    let vChain = `[${i}:v]trim=start=${clip.trimStart}:end=${clip.trimEnd},setpts=(PTS-STARTPTS)/${speed}`
    vChain += `,scale=${WIDTH}:${HEIGHT}:force_original_aspect_ratio=decrease,pad=${WIDTH}:${HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1`
    if (clip.text.trim()) {
      const escaped = escapeDrawtext(clip.text.trim())
      vChain += `,drawtext=fontfile=font.ttf:text='${escaped}':fontcolor=white:fontsize=54:box=1:boxcolor=black@0.5:boxborderw=14:x=(w-text_w)/2:y=${textYExpr(clip.textPosition)}`
    }
    vChain += `[v${i}]`
    parts.push(vChain)

    if (hasAudio[i]) {
      let aChain = `[${i}:a]atrim=start=${clip.trimStart}:end=${clip.trimEnd},asetpts=PTS-STARTPTS,atempo=${speed}`
      aChain += clip.muted ? ',volume=0' : ''
      aChain += `[a${i}]`
      parts.push(aChain)
    } else {
      parts.push(`anullsrc=channel_layout=stereo:sample_rate=44100:d=${outDuration.toFixed(3)}[a${i}]`)
    }
  })

  const concatInputs = clips.map((_, i) => `[v${i}][a${i}]`).join('')
  parts.push(`${concatInputs}concat=n=${clips.length}:v=1:a=1[outv][outa]`)

  return { filter: parts.join(';'), inputArgs }
}

export interface ExportProgress {
  ratio: number
  message: string
}

export async function exportTimeline(
  clips: Clip[],
  onProgress: (progress: ExportProgress) => void,
): Promise<Blob> {
  if (clips.length === 0) {
    throw new Error('Add at least one clip before exporting.')
  }

  onProgress({ ratio: 0, message: 'Loading video engine...' })
  const ffmpeg = await getFFmpeg()

  const recentLogs: string[] = []
  const onLog = ({ message }: { message: string }) => {
    recentLogs.push(message)
    if (recentLogs.length > 40) recentLogs.shift()
  }
  ffmpeg.on('log', onLog)

  const onFfmpegProgress = ({ progress }: { progress: number }) => {
    const ratio = Math.min(0.95, Math.max(0, progress))
    onProgress({ ratio, message: `Rendering... ${Math.round(ratio * 100)}%` })
  }
  ffmpeg.on('progress', onFfmpegProgress)

  onProgress({ ratio: 0.02, message: 'Loading clips...' })
  const hasAudio: boolean[] = []
  for (let i = 0; i < clips.length; i++) {
    const data = await fetchFile(clips[i].file)
    await ffmpeg.writeFile(`input${i}.mp4`, data)
    hasAudio.push(await probeHasAudio(ffmpeg, `input${i}.mp4`))
  }

  if (clips.some((clip) => clip.text.trim())) {
    await ensureFontLoaded(ffmpeg)
  }

  const { filter, inputArgs } = buildFilterComplex(clips, hasAudio)

  onProgress({ ratio: 0.05, message: 'Rendering...' })
  try {
    const exitCode = await ffmpeg.exec([
      ...inputArgs,
      '-filter_complex',
      filter,
      '-map',
      '[outv]',
      '-map',
      '[outa]',
      '-c:v',
      'libx264',
      '-preset',
      'ultrafast',
      '-crf',
      '23',
      '-c:a',
      'aac',
      'output.mp4',
    ])
    if (exitCode !== 0) {
      throw new Error(`ffmpeg exited with code ${exitCode}:\n${recentLogs.join('\n')}`)
    }

    onProgress({ ratio: 0.97, message: 'Finalizing...' })
    const data = await ffmpeg.readFile('output.mp4')
    const bytes = data as Uint8Array

    for (let i = 0; i < clips.length; i++) {
      await ffmpeg.deleteFile(`input${i}.mp4`)
    }
    await ffmpeg.deleteFile('output.mp4')

    onProgress({ ratio: 1, message: 'Done' })
    return new Blob([bytes.slice()], { type: 'video/mp4' })
  } finally {
    ffmpeg.off('log', onLog)
    ffmpeg.off('progress', onFfmpegProgress)
  }
}
