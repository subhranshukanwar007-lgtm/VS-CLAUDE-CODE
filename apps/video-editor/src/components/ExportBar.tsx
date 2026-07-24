import { useState } from 'react'
import type { Clip } from '../types'
import { exportTimeline } from '../lib/export'

interface Props {
  clips: Clip[]
}

export function ExportBar({ clips }: Props) {
  const [status, setStatus] = useState<'idle' | 'working' | 'done' | 'error'>('idle')
  const [message, setMessage] = useState('')
  const [ratio, setRatio] = useState(0)
  const [resultUrl, setResultUrl] = useState<string | null>(null)

  async function handleExport() {
    setStatus('working')
    setRatio(0)
    setResultUrl(null)
    try {
      const blob = await exportTimeline(clips, (progress) => {
        setRatio(progress.ratio)
        setMessage(progress.message)
      })
      setResultUrl(URL.createObjectURL(blob))
      setStatus('done')
    } catch (err) {
      console.error(err)
      setMessage(err instanceof Error ? err.message : 'Export failed.')
      setStatus('error')
    }
  }

  return (
    <div className="export-bar">
      <button type="button" disabled={clips.length === 0 || status === 'working'} onClick={handleExport}>
        {status === 'working' ? 'Exporting...' : 'Export video'}
      </button>

      {status === 'working' && (
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${Math.round(ratio * 100)}%` }} />
        </div>
      )}
      {(status === 'working' || status === 'error') && <p className="export-message">{message}</p>}

      {status === 'done' && resultUrl && (
        <div className="export-result">
          <video src={resultUrl} controls className="export-video" />
          <a href={resultUrl} download="edited-video.mp4" className="download-link">
            Download edited-video.mp4
          </a>
        </div>
      )}
    </div>
  )
}
