<script setup lang="ts">
/**
 * 申込画面。本番では既存の申込フォーム（クライゼルなどのフォーム SaaS）が担うことが多い部分を、このサンプルでは Vue で作っている。
 *
 * 入力欄の部品は Base UI（base-ui-vue）で組み、見た目はデジタル庁デザインシステム（DADS）に合わせている。
 * 入力チェックの中身は validators.ts にあり、Base UI にはエラーの「表示と紐づけ」だけを任せている。
 */
import { Button } from 'base-ui-vue'
import { computed, nextTick, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import DateField from '@/components/DateField.vue'
import ErrorSummary, { type ErrorItem } from '@/components/ErrorSummary.vue'
import FormField from '@/components/FormField.vue'
import NotificationBanner from '@/components/NotificationBanner.vue'
import RadioField, { type RadioOption } from '@/components/RadioField.vue'
import { SAMPLES, type Sample } from '@/samples'
import { useApplicationStore } from '@/stores/application'
import type { ApplicationForm } from '@/types'
import { toPayload, validateApplication } from '@/validators'

const router = useRouter()
const store = useApplicationStore()

// reactive = オブジェクトをまるごとリアクティブにする。form.name = 'x' のように直接書き換えてよい
const form = reactive<ApplicationForm>({
  name: '',
  birth_date: '',
  gender: '',
  postal_code: '',
  address: '',
  phone: '',
  email: '',
  plan: '',
})

const submitted = ref(false)
const submitting = ref(false)
const serverError = ref('')

// form のどの項目が変わっても自動で再計算される（依存配列は不要）
const errors = computed(() => validateApplication(form))
const shownErrors = computed(() => (submitted.value ? errors.value : {}))
const hasErrors = computed(() => Object.keys(errors.value).length > 0)

/** 項目名。入力欄のラベルと、エラーのまとめの両方で使う */
const LABELS: Record<keyof ApplicationForm, string> = {
  name: '氏名',
  birth_date: '生年月日',
  gender: '性別',
  postal_code: '郵便番号',
  address: '住所',
  phone: '電話番号',
  email: 'メールアドレス',
  plan: '料金プラン',
}

// 性別は任意。「回答しない」は '' で表し、API には null で送る（validators.ts の toPayload）
const genderOptions: RadioOption[] = [
  { value: 'male', label: '男性' },
  { value: 'female', label: '女性' },
  { value: '', label: '回答しない' },
]
const planOptions: RadioOption[] = [
  { value: 'light', label: 'ライト', description: '月 3GB まで' },
  { value: 'standard', label: 'スタンダード', description: '月 20GB まで' },
  { value: 'unlimited', label: '無制限', description: 'データ量の上限なし' },
]

/** エラーのまとめ。画面に並んでいる順に出し、リンクで各入力欄へ移動できるようにする */
const errorItems = computed<ErrorItem[]>(() =>
  (Object.keys(LABELS) as (keyof ApplicationForm)[]).flatMap((key) => {
    const message = shownErrors.value[key]
    if (!message) return []
    // 生年月日は3つの欄に分かれているので、先頭の「年」へ移動する
    const targetId = key === 'birth_date' ? 'field-birth_date-year' : `field-${key}`
    return [{ targetId, label: LABELS[key], message }]
  }),
)

const summary = ref<InstanceType<typeof ErrorSummary> | null>(null)

function fillSample(sample: Sample) {
  Object.assign(form, sample.form)
  submitted.value = false
  serverError.value = ''
}

async function submit() {
  if (submitting.value) return
  submitted.value = true
  serverError.value = ''
  if (hasErrors.value) {
    // エラーのまとめが描画されるのを待ってから、そこへフォーカスを移す
    await nextTick()
    summary.value?.focus()
    return
  }

  submitting.value = true
  try {
    const created = await api.createApplication(toPayload(form))
    store.setSession(created.application_id, created.handoff_token)
    await router.push({ name: 'ekyc' })
  } catch (e) {
    serverError.value = e instanceof ApiError ? e.message : '申込を送信できませんでした。'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="card sample-box" aria-labelledby="sample-title">
    <h2 id="sample-title" class="card__title">サンプル入力<span class="tag">学習用</span></h2>
    <p class="card__lead">ボタンを押すとフォームに入力されます。本人確認のモック画面で、書かれている人物を選んでください。</p>
    <div class="sample-list">
      <button v-for="s in SAMPLES" :key="s.key" type="button" class="sample" @click="fillSample(s)">
        <strong>{{ s.label }}</strong>
        <span>{{ s.howTo }}</span>
      </button>
    </div>
  </section>

  <!-- @submit.prevent = onSubmit で e.preventDefault() するのと同じ -->
  <form class="card form" novalidate aria-labelledby="form-title" @submit.prevent="submit">
    <h2 id="form-title" class="card__title">お申込み内容</h2>
    <p class="card__lead">マイナンバーカードに記載のとおりに入力してください。</p>

    <ErrorSummary v-if="errorItems.length" ref="summary" :items="errorItems" />

    <div class="form__fields">
      <FormField v-model="form.name" name="name" :label="LABELS.name" required autocomplete="name"
        hint="姓と名の間にスペースを入れてください。例: 山田 太郎" :error="shownErrors.name" />
      <DateField v-model="form.birth_date" name="birth_date" :label="LABELS.birth_date" required
        hint="西暦で入力してください。例: 1990年4月1日" :error="shownErrors.birth_date" />
      <RadioField v-model="form.gender" name="gender" :label="LABELS.gender" :options="genderOptions"
        :error="shownErrors.gender" />
      <FormField v-model="form.postal_code" name="postal_code" :label="LABELS.postal_code" required
        autocomplete="postal-code" inputmode="numeric" :maxlength="8" width="short"
        hint="例: 100-0001" :error="shownErrors.postal_code" />
      <FormField v-model="form.address" name="address" :label="LABELS.address" required
        autocomplete="street-address" hint="建物名・部屋番号まで入力してください。例: 東京都千代田区サンプル町1-2-3 サンプルハイツ101"
        :error="shownErrors.address" />
      <FormField v-model="form.phone" name="phone" :label="LABELS.phone" type="tel" required autocomplete="tel"
        width="medium" hint="例: 090-1234-5678" :error="shownErrors.phone" />
      <FormField v-model="form.email" name="email" :label="LABELS.email" type="email" required
        autocomplete="email" hint="例: taro@example.com" :error="shownErrors.email" />
      <RadioField v-model="form.plan" name="plan" :label="LABELS.plan" required :options="planOptions"
        variant="tile" :error="shownErrors.plan" />
    </div>

    <NotificationBanner v-if="serverError" type="error" title="お申込みを送信できませんでした" role="alert">
      <p class="banner__text">{{ serverError }}</p>
    </NotificationBanner>

    <!-- 送信中は aria-disabled にする（DADS の無効状態。フォーカスは外さず、押しても反応しない） -->
    <Button type="submit" class="button button--primary button--block" :disabled="submitting" focusable-when-disabled>
      {{ submitting ? '送信しています…' : '申し込んで本人確認へ進む' }}
    </Button>
  </form>
</template>
