import type { ApplicationForm, ApplicationPayload, Gender, Plan } from '@/types'

export type FormErrors = Partial<Record<keyof ApplicationForm, string>>

export const MIN_AGE = 18

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
