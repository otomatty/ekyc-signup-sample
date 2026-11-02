import type { ApplicationForm, ApplicationPayload, Gender, Plan } from '@/types'

export type FormErrors = Partial<Record<keyof ApplicationForm, string>>

export const MIN_AGE = 18

/** 生年月日の入力欄（年・月・日を別々に入力する）で扱う値 */
export interface DateParts {
  year: string
  month: string
  day: string
}

/** 全角数字を半角にし、前後の空白を除く。年月日の入力欄は全角で入力されることもある */
function toHalfWidthDigits(value: string): string {
  return value.replace(/[０-９]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0)).trim()
}

/** 年・月・日を 'YYYY-MM-DD' にまとめる。すべて空なら ''（未入力）を返す */
export function joinDateParts(parts: DateParts): string {
  const year = toHalfWidthDigits(parts.year)
  const month = toHalfWidthDigits(parts.month)
  const day = toHalfWidthDigits(parts.day)
  if (!year && !month && !day) return ''
  const pad = (v: string) => (/^\d$/.test(v) ? `0${v}` : v)
  return `${year}-${pad(month)}-${pad(day)}`
}

/** 'YYYY-MM-DD' を年・月・日に分ける（サンプル入力などで外から値が入ったときに使う） */
export function splitDate(value: string): DateParts {
  const [year = '', month = '', day = ''] = value ? value.split('-') : []
  return { year, month, day }
}

/** 'YYYY-MM-DD' の形で、実在する日付か（2月30日などを弾く） */
export function isValidDate(value: string): boolean {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!m) return false
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])]
  const date = new Date(Date.UTC(y, mo - 1, d))
  return date.getUTCFullYear() === y && date.getUTCMonth() === mo - 1 && date.getUTCDate() === d
}

export function ageOn(birthDate: string, today: Date): number {
  const [y, m, d] = birthDate.split('-').map(Number)
  if (!y || !m || !d) return Number.NaN
  const beforeBirthday =
    today.getMonth() + 1 < m || (today.getMonth() + 1 === m && today.getDate() < d)
  return today.getFullYear() - y - (beforeBirthday ? 1 : 0)
}

/** 画面側の入力チェック。サーバー側（Pydantic）でも同じ内容をチェックする */
export function validateApplication(form: ApplicationForm, today = new Date()): FormErrors {
  const errors: FormErrors = {}
  const name = form.name.trim()

  if (!name) errors.name = '氏名を入力してください'
  else if (!/[ 　]/.test(name)) errors.name = '姓と名の間にスペースを入れてください'

  if (!form.birth_date) errors.birth_date = '生年月日を入力してください'
  else if (!isValidDate(form.birth_date))
    errors.birth_date = '生年月日を確認してください（例: 1990年4月1日）'
  else if (!(ageOn(form.birth_date, today) >= MIN_AGE))
    errors.birth_date = `${MIN_AGE}歳以上の方のみお申込みいただけます`

  if (!/^\d{3}-?\d{4}$/.test(form.postal_code))
    errors.postal_code = '郵便番号は7桁で入力してください（例: 100-0001）'

  if (!form.address.trim()) errors.address = '住所を入力してください'

  if (!/^0\d{1,4}-?\d{1,4}-?\d{3,4}$/.test(form.phone))
    errors.phone = '電話番号を確認してください（例: 090-1234-5678）'

  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email))
    errors.email = 'メールアドレスを確認してください'

  if (!form.plan) errors.plan = 'プランを選んでください'

  return errors
}

export function toPayload(form: ApplicationForm): ApplicationPayload {
  return {
    name: form.name.trim(),
    birth_date: form.birth_date,
    gender: form.gender ? (form.gender as Gender) : null,
    postal_code: form.postal_code,
    address: form.address.trim(),
    phone: form.phone,
    email: form.email,
    plan: form.plan as Plan,
  }
}
