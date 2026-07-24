import type { Clip } from '../types'
import { formatTime } from '../lib/format'

interface Props {
  clips: Clip[]
  selectedId: string | null
  onSelect: (id: string) => void
  onUpdate: (id: string, patch: Partial<Clip>) => void
  onRemove: (id: string) => void
  onMove: (id: string, direction: -1 | 1) => void
}

export function ClipTimeline({ clips, selectedId, onSelect, onUpdate, onRemove, onMove }: Props) {
  if (clips.length === 0) {
    return <p className="empty-hint">No clips yet — add a video above to start editing.</p>
  }

  return (
    <div className="clip-list">
      {clips.map((clip, index) => (
        <div
          key={clip.id}
          className={`clip-card${clip.id === selectedId ? ' selected' : ''}`}
          onClick={() => onSelect(clip.id)}
        >
          <div className="clip-card-header">
            <span className="clip-index">{index + 1}</span>
            <span className="clip-name" title={clip.name}>
              {clip.name}
            </span>
            <div className="clip-actions" onClick={(e) => e.stopPropagation()}>
              <button type="button" disabled={index === 0} onClick={() => onMove(clip.id, -1)} title="Move earlier">
                ↑
              </button>
              <button
                type="button"
                disabled={index === clips.length - 1}
                onClick={() => onMove(clip.id, 1)}
                title="Move later"
              >
                ↓
              </button>
              <button type="button" className="danger" onClick={() => onRemove(clip.id)} title="Remove clip">
                ✕
              </button>
            </div>
          </div>

          <div className="clip-controls" onClick={(e) => e.stopPropagation()}>
            <label className="field">
              <span>
                Trim {formatTime(clip.trimStart)} – {formatTime(clip.trimEnd)}
              </span>
              <div className="dual-range">
                <input
                  type="range"
                  min={0}
                  max={clip.duration}
                  step={0.1}
                  value={clip.trimStart}
                  onChange={(e) => {
                    const v = Math.min(Number(e.target.value), clip.trimEnd - 0.1)
                    onUpdate(clip.id, { trimStart: Math.max(0, v) })
                  }}
                />
                <input
                  type="range"
                  min={0}
                  max={clip.duration}
                  step={0.1}
                  value={clip.trimEnd}
                  onChange={(e) => {
                    const v = Math.max(Number(e.target.value), clip.trimStart + 0.1)
                    onUpdate(clip.id, { trimEnd: Math.min(clip.duration, v) })
                  }}
                />
              </div>
            </label>

            <div className="field-row">
              <label className="field">
                <span>Speed {clip.speed.toFixed(2)}x</span>
                <input
                  type="range"
                  min={0.5}
                  max={2}
                  step={0.05}
                  value={clip.speed}
                  onChange={(e) => onUpdate(clip.id, { speed: Number(e.target.value) })}
                />
              </label>

              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={clip.muted}
                  onChange={(e) => onUpdate(clip.id, { muted: e.target.checked })}
                />
                <span>Mute</span>
              </label>
            </div>

            <div className="field-row">
              <label className="field grow">
                <span>Text overlay</span>
                <input
                  type="text"
                  placeholder="Add a caption..."
                  value={clip.text}
                  onChange={(e) => onUpdate(clip.id, { text: e.target.value })}
                />
              </label>

              <label className="field">
                <span>Position</span>
                <select
                  value={clip.textPosition}
                  onChange={(e) => onUpdate(clip.id, { textPosition: e.target.value as Clip['textPosition'] })}
                >
                  <option value="top">Top</option>
                  <option value="middle">Middle</option>
                  <option value="bottom">Bottom</option>
                </select>
              </label>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
