# Video Editor

A browser-based video editor: trim, reorder, mute, speed up, caption, and stitch clips
together into a single export. Everything runs client-side via [FFmpeg.wasm](https://ffmpegwasm.netlify.app/)
— no server, no uploads, works offline once the page has loaded.

## Features

- Drag-and-drop (or click to browse) video upload, multiple clips at once
- Per-clip trim range, playback speed (0.5x–2x), mute, and text overlay (with position)
- Reorder clips before exporting
- Live preview of the trimmed range for the selected clip
- Export renders all clips (with effects applied) and concatenates them into a single
  downloadable `.mp4`

## Getting started

```bash
npm install
npm run dev
```

Then open the printed local URL in your browser.

`npm install` also copies the FFmpeg WebAssembly core into `public/ffmpeg/` (via
`scripts/copy-ffmpeg-core.mjs`) so the app doesn't depend on a CDN at runtime.

## How it works

- `src/lib/ffmpeg.ts` loads a single shared FFmpeg.wasm instance.
- `src/lib/export.ts` builds an ffmpeg `filter_complex` graph: each clip is trimmed,
  speed-adjusted, scaled to a common resolution, optionally captioned (via `drawtext`,
  using the bundled DejaVu Sans font since the wasm build has no system fonts), then
  all clips are joined with the `concat` filter. Clips without an audio track (detected
  via `ffprobe`) get a silent track synthesized with `anullsrc` so `concat` always sees
  matching stream counts.
- Everything happens in the browser's WebAssembly runtime — no video data ever leaves
  the machine.

## Notes / limitations

- This is a from-scratch client-side editor (no timeline scrubbing across multiple
  clips yet, no transitions) — trim, speed, mute, and text overlay per clip, then concat.
- Rendering speed depends on the browser's CPU (WebAssembly, single-threaded); large or
  many clips will take longer to export than a native editor would.
- `DejaVuSans.ttf` (used for caption rendering) is bundled under the Bitstream Vera
  License — see `public/fonts/DejaVuSans-LICENSE.txt`.

## Build

```bash
npm run build
npm run preview
```
