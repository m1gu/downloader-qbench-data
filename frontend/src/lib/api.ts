import { API_BASE_URL } from '../config'

type QueryValue = string | number | boolean | undefined | null

type QueryParams = Record<string, QueryValue>

function buildUrl(path: string, params?: QueryParams): string {
  const base = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  let url = `${base}${normalizedPath}`

  if (params) {
    const searchParams = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value === null || value === undefined || value === '') continue
      searchParams.append(key, String(value))
    }
    const queryString = searchParams.toString()
    if (queryString) {
      url += `?${queryString}`
    }
  }

  return url
}

export async function apiFetch<T>(path: string, params?: QueryParams, init?: RequestInit): Promise<T> {
  const url = buildUrl(path, params)
  const response = await fetch(url, {
    headers: {
      Accept: 'application/json',
    },
    ...init,
  })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const parsed = (await response.json()) as { detail?: string }
      if (parsed?.detail) {
        detail = parsed.detail
      }
    } catch {
      // ignore JSON parsing errors, keep status text
    }
    throw new Error(`API request failed (${response.status}): ${detail}`)
  }

  return (await response.json()) as T
}
