import { useRef, useState } from 'react'
import type { DragEvent } from 'react'

interface Props {
  onFiles: (files: File[]) => void
}

export function UploadZone({ onFiles }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(false)
    const files = Array.from(e.dataTransfer.files).filter((f) => f.type.startsWith('video/'))
    if (files.length) onFiles(files)
  }

  return (
    <div
      className={`upload-zone${dragging ? ' dragging' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <p className="upload-title">Drop video files here, or click to browse</p>
      <p className="upload-hint">Processing happens entirely in your browser — nothing is uploaded anywhere.</p>
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        multiple
        hidden
        onChange={(e) => {
          const files = Array.from(e.target.files ?? [])
          if (files.length) onFiles(files)
          e.target.value = ''
        }}
      />
    </div>
  )
}
