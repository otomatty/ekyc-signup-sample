<script setup lang="ts">
/**
 * 申込画面。本番では既存の申込フォーム（クライゼルなどのフォーム SaaS）が担うことが多い部分を、このサンプルでは Vue で作っている。
 */
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import FormField from '@/components/FormField.vue'
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

const genderOptions = [
  { value: 'male', label: '男性' },
  { value: 'female', label: '女性' },
]
const planOptions = [
  { value: 'light', label: 'ライト（3GB）' },
  { value: 'standard', label: 'スタンダード（20GB）' },
  { value: 'unlimited', label: '無制限' },
]

function fillSample(sample: Sample) {
  Object.assign(form, sample.form)
  submitted.value = false
  serverError.value = ''
}

async function submit() {
  submitted.value = true
  serverError.value = ''
  if (hasErrors.value) return

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
  <section class="card sample-box">
    <h2>サンプル入力</h2>
    <p class="muted">ボタンを押すとフォームに入力されます。本人確認のモック画面で、書かれている人物を選んでください。</p>
    <div class="sample-list">
      <button v-for="s in SAMPLES" :key="s.key" type="button" class="sample" @click="fillSample(s)">
        <strong>{{ s.label }}</strong>
        <span>{{ s.howTo }}</span>
      </button>
    </div>
  </section>

  <!-- @submit.prevent = onSubmit で e.preventDefault() するのと同じ -->
  <form class="card" novalidate @submit.prevent="submit">
    <h2>お申込み内容</h2>
    <p class="muted">マイナンバーカードと同じ内容で入力してください。</p>

    <FormField v-model="form.name" name="name" label="氏名" required autocomplete="name"
      placeholder="山田 太郎" hint="姓と名の間にスペースを入れてください" :error="shownErrors.name" />
    <FormField v-model="form.birth_date" name="birth_date" label="生年月日" type="date" required
      autocomplete="bday" :error="shownErrors.birth_date" />
    <FormField v-model="form.gender" name="gender" label="性別" :options="genderOptions"
      empty-option-label="回答しない" :error="shownErrors.gender" />
    <FormField v-model="form.postal_code" name="postal_code" label="郵便番号" required
      autocomplete="postal-code" placeholder="100-0001" :error="shownErrors.postal_code" />
    <FormField v-model="form.address" name="address" label="住所" required autocomplete="street-address"
      placeholder="東京都千代田区サンプル町1-2-3 サンプルハイツ101" :error="shownErrors.address" />
    <FormField v-model="form.phone" name="phone" label="電話番号" type="tel" required autocomplete="tel"
      placeholder="090-1234-5678" :error="shownErrors.phone" />
    <FormField v-model="form.email" name="email" label="メールアドレス" type="email" required
      autocomplete="email" :error="shownErrors.email" />
    <FormField v-model="form.plan" name="plan" label="料金プラン" required :options="planOptions"
      :error="shownErrors.plan" />

    <p v-if="serverError" class="alert alert-danger" role="alert">{{ serverError }}</p>
    <p v-else-if="submitted && hasErrors" class="alert alert-danger" role="alert">入力内容を確認してください。</p>

    <button type="submit" class="btn btn-primary" :disabled="submitting">
      {{ submitting ? '送信中…' : '申し込んで本人確認へ進む' }}
    </button>
  </form>
</template>
