import type { ApplicationForm } from '@/types'

/**
 * 「サンプル入力」ボタンの中身。
 * モックベンダー画面で、同じ人物のテスト用カードを選ぶと各ケースを再現できる
 * （backend/app/mock_vendor/personas.py と対応）。
 */
export interface Sample {
  key: string
  label: string
  howTo: string
  form: ApplicationForm
}

export const SAMPLES: Sample[] = [
  {
    key: 'match',
    label: '一致する',
    howTo: 'モック画面で「山田 太郎」を選ぶ → 本人確認完了',
    form: {
      name: '山田 太郎',
      birth_date: '1990-04-01',
      gender: 'male',
      postal_code: '100-0001',
      address: '東京都千代田区サンプル町1-2-3 サンプルハイツ101',
      phone: '090-1234-5678',
      email: 'taro@example.com',
      plan: 'standard',
    },
  },
  {
    key: 'itaiji',
    label: '異体字',
    howTo: 'モック画面で「髙橋 花子」を選ぶ → 担当者確認',
    form: {
      name: '高橋 花子',
      birth_date: '1985-11-20',
      gender: 'female',
      postal_code: '220-0011',
      address: '神奈川県横浜市西区みなと見本2-5-8',
      phone: '080-2345-6789',
      email: 'hanako@example.com',
      plan: 'light',
    },
  },
  {
    key: 'building',
    label: '建物名の有無',
    howTo: 'モック画面で「鈴木 一郎」を選ぶ → 担当者確認',
    form: {
      name: '鈴木 一郎',
      birth_date: '1972-02-29',
      gender: 'male',
      postal_code: '330-0001',
      address: '埼玉県さいたま市大宮区見本台4-5-6 ミライタワー2003',
      phone: '070-3456-7890',
      email: 'ichiro@example.com',
      plan: 'unlimited',
    },
  },
  {
    key: 'moved',
    label: '住所が違う',
    howTo: 'モック画面で「佐藤 次郎」を選ぶ → 本人確認NG',
    form: {
      name: '佐藤 次郎',
      birth_date: '1978-07-15',
      gender: 'male',
      postal_code: '530-0001',
      address: '大阪府大阪市北区新住所町1-1-1',
      phone: '090-4567-8901',
      email: 'jiro@example.com',
      plan: 'standard',
    },
  },
]
