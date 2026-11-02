<script setup lang="ts">
import { Button } from 'base-ui-vue'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import NotificationBanner from '@/components/NotificationBanner.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { usePolling } from '@/composables/usePolling'
import { useApplicationStore } from '@/stores/application'
import { SETTLED_STATUSES, type MatchItem } from '@/types'

const router = useRouter()
const store = useApplicationStore()

// ベンダーからの結果（コールバック）は少し遅れて届くため、確定するまで定期的に取りに行く
const { data, error, isPolling, timedOut, start } = usePolling(
  () => api.getStatus(store.applicationId!, store.handoffToken!),
  { isDone: (s) => SETTLED_STATUSES.includes(s.status), intervalMs: 1500 },
)

// onMounted = 画面に表示された直後に1回だけ動く（useEffect(..., []) に相当）
onMounted(start)

const RESULT_TEXT: Record<MatchItem['result'], string> = {
  MATCH: '一致',
  PARTIAL: '要確認',
  MISMATCH: '不一致',
  SKIPPED: '対象外',
}

function retry() {
  router.push({ name: 'ekyc' })
}

function startOver() {
  store.clear()
  router.push({ name: 'apply' })
}
</script>

<template>
  <section class="card" aria-live="polite" aria-labelledby="result-title">
    <h2 id="result-title" class="card__title">本人確認の結果</h2>

    <div v-if="!data && isPolling" class="loading">
      <span class="spinner" aria-hidden="true"></span>
      結果を確認しています…
    </div>

    <template v-if="data">
      <div class="result-head">
        <StatusBadge :status="data.status" :label="data.status_label" />
        <span class="result-head__name">{{ data.masked_name }} 様</span>
      </div>
      <p class="result-message">{{ data.message }}</p>

      <div v-if="isPolling" class="loading">
        <span class="spinner" aria-hidden="true"></span>
        ベンダーからの結果を待っています…
      </div>

      <table v-if="data.match_items.length" class="match-table">
        <caption>照合の内訳</caption>
        <thead>
          <tr><th scope="col">項目</th><th scope="col">判定</th><th scope="col">補足</th></tr>
        </thead>
        <tbody>
          <tr v-for="item in data.match_items" :key="item.field">
            <th scope="row">{{ item.label }}</th>
            <td><span class="result" :class="`result-${item.result.toLowerCase()}`">{{ RESULT_TEXT[item.result] }}</span></td>
            <td class="match-table__note">{{ item.note || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </template>

    <NotificationBanner v-if="timedOut" type="info" title="結果の確認に時間がかかっています">
      <p class="banner__text">しばらくしてからこの画面を再読み込みしてください。</p>
    </NotificationBanner>
    <NotificationBanner v-if="error" type="error" title="結果を取得できませんでした" role="alert">
      <p class="banner__text">{{ error.message }}</p>
    </NotificationBanner>

    <div class="actions">
      <Button v-if="data?.can_retry && !isPolling" class="button button--primary button--block" @click="retry">
        もう一度本人確認する
      </Button>
      <Button class="button button--outline button--block" @click="startOver">新しい申込を始める</Button>
    </div>
  </section>
</template>
