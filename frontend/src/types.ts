// API とやり取りする型。backend/app/models.py と対応している

export type Gender = 'male' | 'female'
export type Plan = 'light' | 'standard' | 'unlimited'

/** 画面の入力状態。select の未選択を '' で表すため、すべて文字列で持つ */
export interface ApplicationForm {
  name: string
  birth_date: string
  gender: string
  postal_code: string
  address: string
  phone: string
  email: string
  plan: string
}

/** API に送る形 */
export interface ApplicationPayload {
  name: string
  birth_date: string
  gender: Gender | null
  postal_code: string
  address: string
  phone: string
  email: string
  plan: Plan
}

export type ApplicationStatus =
  | 'APPLIED'
  | 'EKYC_IN_PROGRESS'
  | 'VERIFIED'
  | 'NEEDS_REVIEW'
  | 'REJECTED'
  | 'EKYC_FAILED'

/** これ以上状態が変わらない（ポーリングを止めてよい）状態 */
export const SETTLED_STATUSES: readonly ApplicationStatus[] = [
  'APPLIED',
  'VERIFIED',
  'NEEDS_REVIEW',
  'REJECTED',
  'EKYC_FAILED',
]

export interface MatchItem {
  field: string
  label: string
  result: 'MATCH' | 'PARTIAL' | 'MISMATCH' | 'SKIPPED'
  note: string
}

export interface ApplicationCreated {
  application_id: string
  handoff_token: string
  expires_at: string
}

export interface StatusResponse {
  application_id: string
  status: ApplicationStatus
  status_label: string
  message: string
  masked_name: string
  can_retry: boolean
  match_items: MatchItem[]
  updated_at: string
}

export interface EkycSessionCreated {
  verify_url: string
}
