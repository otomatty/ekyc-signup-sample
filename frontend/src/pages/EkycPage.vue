<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import { useApplicationStore } from '@/stores/application'

const router = useRouter()
const store = useApplicationStore()

const starting = ref(false)
const error = ref('')
const sessionExpired = ref(false)

// 本番では、PC から来た人をスマホへ誘導する（QRコードなど）。ここでは判定して案内だけ出す
const isMobile = computed(() => /iPhone|Android/i.test(navigator.userAgent))

async function start() {
  if (!store.handoffToken) return
  starting.value = true
  error.value = ''
  try {
    const { verify_url } = await api.startEkyc(store.handoffToken)
    // ベンダーの画面へページごと移動する（SPA の外に出る）
    window.location.assign(verify_url)
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) {
      await router.push({ name: 'result' })
      return
    }
    sessionExpired.value = e instanceof ApiError && e.status === 401
    error.value = e instanceof ApiError ? e.message : '本人確認を開始できませんでした。'
    starting.value = false
  }
}

function restart() {
  store.clear()
  router.push({ name: 'apply' })
}
</script>

<template>
  <section class="card">
    <h2>マイナンバーカードで本人確認</h2>
    <p>お申込みにはマイナンバーカードによる本人確認が必要です。次のものをご用意ください。</p>
    <ol class="steps">
      <li>
        <strong>マイナンバーカード</strong>
        <span>電子証明書の有効期限が切れていないもの</span>
      </li>
      <li>
        <strong>署名用電子証明書のパスワード</strong>
        <span>英数字6〜16文字。数字4桁の暗証番号とは別のものです</span>
      </li>
      <li>
        <strong>NFC 対応のスマートフォン</strong>
        <span>カードをスマホの背面にかざして読み取ります</span>
      </li>
    </ol>

    <p v-if="!isMobile" class="alert alert-info">
      PC からアクセスしています。実際のサービスでは、ここで QR コードを表示してスマホに切り替えてもらいます。このサンプルでは、PC のままモック画面に進めます。
    </p>

    <p v-if="error" class="alert alert-danger" role="alert">{{ error }}</p>

    <button v-if="sessionExpired" type="button" class="btn btn-primary" @click="restart">最初からやり直す</button>
    <button v-else type="button" class="btn btn-primary" :disabled="starting" @click="start">
      {{ starting ? '準備しています…' : '本人確認を始める' }}
    </button>
  </section>
</template>
