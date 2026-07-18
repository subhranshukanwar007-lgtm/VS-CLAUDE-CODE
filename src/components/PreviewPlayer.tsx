import { useEffect, useRef } from 'react'
import type { Clip } from '../types'

interface Props {
  clip: Clip | null
}

export function PreviewPlayer({ clip }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    const video = videoRef.current
    if (!video || !clip) return
    video.currentTime = clip.trimStart
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clip?.id, clip?.trimStart])

  useEffect(() => {
    const video = videoRef.current
    if (!video || !clip) return

    function onTimeUpdate() {
      if (!video || !clip) return
      if (video.currentTime >= clip.trimEnd) {
        video.pause()
        video.currentTime = clip.trimStart
      }
    }
    video.addEventListener('timeupdate', onTimeUpdate)
    return () => video.removeEventListener('timeupdate', onTimeUpdate)
  }, [clip])

  if (!clip) {
    return (
      <div className="preview-empty">
        <p>Select a clip to preview it here.</p>
      </div>
    )
  }

  return (
    <div className="preview-player">
      <video ref={videoRef} src={clip.url} controls muted={clip.muted} className="preview-video" />
      <p className="preview-caption">
        Previewing trimmed range ({clip.trimStart.toFixed(1)}s – {clip.trimEnd.toFixed(1)}s). Full effects (speed,
        text overlay) appear in the exported video.
      </p>
    </div>
  )
}
