import { describe, expect, it } from 'vitest'
import type { ApplicationForm } from './types'
import { ageOn, toPayload, validateApplication } from './validators'

const valid: ApplicationForm = {
  name: '山田 太郎',
  birth_date: '1990-04-01',
  gender: 'male',
  postal_code: '100-0001',
  address: '東京都千代田区サンプル町1-2-3',
  phone: '090-1234-5678',
  email: 'taro@example.com',
  plan: 'standard',
}
const today = new Date(2026, 9, 28) // 2026-10-28

describe('validateApplication', () => {
  it('正しい入力ならエラーなし', () => {
    expect(validateApplication(valid, today)).toEqual({})
  })

  it('姓と名の間にスペースがないとエラー', () => {
    expect(validateApplication({ ...valid, name: '山田太郎' }, today).name).toContain('スペース')
  })

  it('全角スペースでもよい', () => {
    expect(validateApplication({ ...valid, name: '山田　太郎' }, today).name).toBeUndefined()
  })

  it('18歳未満はエラー', () => {
    expect(validateApplication({ ...valid, birth_date: '2010-01-01' }, today).birth_date).toContain('18歳')
  })

  it('誕生日の前日はまだ17歳', () => {
    expect(ageOn('2008-10-29', today)).toBe(17)
    expect(ageOn('2008-10-28', today)).toBe(18)
  })

  it('未入力の項目をまとめて返す', () => {
    const empty = Object.fromEntries(Object.keys(valid).map((k) => [k, ''])) as unknown as ApplicationForm
    const errors = validateApplication(empty, today)
    expect(Object.keys(errors).sort()).toEqual(
      ['address', 'birth_date', 'email', 'name', 'phone', 'plan', 'postal_code'].sort(),
    )
  })
})

describe('toPayload', () => {
  it('性別の未回答は null にする', () => {
    expect(toPayload({ ...valid, gender: '' }).gender).toBeNull()
  })
})
