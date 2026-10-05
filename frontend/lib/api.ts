import type { EnrichResponse, ModelInfo, PredictResponse } from './types'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function extractDetail(body: unknown, status: number): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : String(d)))
        .join('; ')
    }
  }
  return `Request failed with status ${status}.`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError('Could not reach the ProtClass API. Is the backend running?', 0)
  }
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (!res.ok) throw new ApiError(extractDetail(body, res.status), res.status)
  return body as T
}

// All calls use same-origin relative URLs: in production FastAPI serves this
// static build and the /api routes together; in `npm run dev` Next.js proxies
// /api/* to the backend (see next.config.mjs).
export const api = {
  health: (): Promise<{ status: string; model_loaded: boolean }> => request('/api/health'),

  modelInfo: (): Promise<ModelInfo> => request<ModelInfo>('/api/model-info'),

  predict: (sequence: string): Promise<PredictResponse> =>
    request<PredictResponse>('/api/predict', {
      method: 'POST',
      body: JSON.stringify({ sequence }),
    }),

  enrich: (accession: string): Promise<EnrichResponse> =>
    request<EnrichResponse>(`/api/enrich/${encodeURIComponent(accession)}`),
}
