import { PHASE_DEVELOPMENT_SERVER } from 'next/constants.js'

// Two modes:
//  - `npm run build` -> static export into frontend/out/, which FastAPI serves at /
//    alongside the /api routes (one origin, one `uvicorn` command).
//  - `npm run dev`   -> Next.js dev server with hot reload; /api/* is proxied to the
//    FastAPI backend (default http://localhost:8000, override with PROTCLASS_API_URL).
export default function nextConfig(phase) {
  const common = {
    images: { unoptimized: true },
  }

  if (phase === PHASE_DEVELOPMENT_SERVER) {
    const backend = (process.env.PROTCLASS_API_URL || 'http://localhost:8000').replace(/\/$/, '')
    return {
      ...common,
      async rewrites() {
        return [{ source: '/api/:path*', destination: `${backend}/api/:path*` }]
      },
    }
  }

  return { ...common, output: 'export' }
}
