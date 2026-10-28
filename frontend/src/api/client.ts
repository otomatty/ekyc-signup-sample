import type {
  ApplicationCreated,
  ApplicationPayload,
  EkycSessionCreated,
  StatusResponse,
} from '@/types'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** FastAPI のエラー応答（{ detail: ... }）から、利用者に見せるメッセージを取り出す */
function messageFrom(body: unknown, status: number): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      // 入力チェックのエラー（422）は配列で返ってくる
      const messages = detail
        .map((d) => String((d as { msg?: unknown }).msg ?? '').replace(/^Value error, /, ''))
        .filter(Boolean)
      if (messages.length) return messages.join('\n')
    }
  }
  if (status >= 500) return 'サーバーでエラーが発生しました。時間をおいてお試しください。'
  return '通信に失敗しました。'
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init.headers },
    })
  } catch {
    throw new ApiError(0, 'ネットワークに接続できません。')
  }
  if (!res.ok) {
    let body: unknown = null
    try {
      body = await res.json()
    } catch {
      // 本文が JSON でないときは無視する
    }
    throw new ApiError(res.status, messageFrom(body, res.status))
  }
  return (await res.json()) as T
}

export const api = {
  createApplication(payload: ApplicationPayload) {
    return request<ApplicationCreated>('/api/applications', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  getStatus(applicationId: string, handoffToken: string) {
    return request<StatusResponse>(`/api/applications/${encodeURIComponent(applicationId)}`, {
      headers: { Authorization: `Bearer ${handoffToken}` },
    })
  },

  startEkyc(handoffToken: string) {
    return request<EkycSessionCreated>('/api/ekyc/sessions', {
      method: 'POST',
      body: JSON.stringify({ handoff_token: handoffToken }),
    })
  },
}
