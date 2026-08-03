# Social Media AI OS — Frontend

Next.js 16 (App Router) + TypeScript + Tailwind v4 dashboard. See the
[repo root README](../../README.md) for the full picture and
[`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) for how this fits with
the backend.

## Development

```bash
npm install
cp .env.local.example .env.local   # points NEXT_PUBLIC_API_URL at the backend
npm run dev
```

Requires `apps/api` running (see `../api/README.md`) at the URL in
`NEXT_PUBLIC_API_URL`.

## Scripts

- `npm run dev` — dev server (Turbopack)
- `npm run build` — production build
- `npm run lint` — ESLint
- `npx tsc --noEmit` — type-check
