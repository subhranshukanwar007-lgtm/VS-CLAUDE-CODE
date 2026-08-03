import { useEffect, useState } from 'react'
import './App.css'
import { UploadZone } from './components/UploadZone'
import { ClipTimeline } from './components/ClipTimeline'
import { PreviewPlayer } from './components/PreviewPlayer'
import { ExportBar } from './components/ExportBar'
import type { Clip } from './types'

function readDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.onloadedmetadata = () => {
      resolve(video.duration)
      URL.revokeObjectURL(video.src)
    }
    video.onerror = () => reject(new Error(`Could not read metadata for ${file.name}`))
    video.src = URL.createObjectURL(file)
  })
}

function App() {
  const [clips, setClips] = useState<Clip[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    return () => {
      clips.forEach((clip) => URL.revokeObjectURL(clip.url))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleFiles(files: File[]) {
    const newClips = await Promise.all(
      files.map(async (file) => {
        const duration = await readDuration(file)
        const clip: Clip = {
          id: crypto.randomUUID(),
          file,
          url: URL.createObjectURL(file),
          name: file.name,
          duration,
          trimStart: 0,
          trimEnd: duration,
          muted: false,
          speed: 1,
          text: '',
          textPosition: 'bottom',
        }
        return clip
      }),
    )
    setClips((prev) => [...prev, ...newClips])
    setSelectedId((prev) => prev ?? newClips[0]?.id ?? null)
  }

  function updateClip(id: string, patch: Partial<Clip>) {
    setClips((prev) => prev.map((c) => (c.id === id ? { ...c, ...patch } : c)))
  }

  function removeClip(id: string) {
    setClips((prev) => {
      const clip = prev.find((c) => c.id === id)
      if (clip) URL.revokeObjectURL(clip.url)
      const next = prev.filter((c) => c.id !== id)
      if (selectedId === id) setSelectedId(next[0]?.id ?? null)
      return next
    })
  }

  function moveClip(id: string, direction: -1 | 1) {
    setClips((prev) => {
      const index = prev.findIndex((c) => c.id === id)
      const target = index + direction
      if (index < 0 || target < 0 || target >= prev.length) return prev
      const next = [...prev]
      ;[next[index], next[target]] = [next[target], next[index]]
      return next
    })
  }

  const selectedClip = clips.find((c) => c.id === selectedId) ?? null

  return (
    <div className="app">
      <header className="app-header">
        <h1>Video Editor</h1>
        <p>Trim, reorder, mute, speed up, caption, and stitch clips together — all in your browser.</p>
      </header>

      <main className="app-main">
        <section className="panel">
          <UploadZone onFiles={handleFiles} />
          <ClipTimeline
            clips={clips}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onUpdate={updateClip}
            onRemove={removeClip}
            onMove={moveClip}
          />
        </section>

        <section className="panel panel-preview">
          <h2>Preview</h2>
          <PreviewPlayer clip={selectedClip} />
          <h2>Export</h2>
          <ExportBar clips={clips} />
        </section>
      </main>
    </div>
  )
}

export default App
