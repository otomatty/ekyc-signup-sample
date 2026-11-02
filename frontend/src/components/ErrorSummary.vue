<script setup lang="ts">
/**
 * 送信時のエラーのまとめ。フォームの先頭に出し、各項目へのリンクを並べる。
 * 送信ボタンを押したらここにフォーカスを移すので、スクリーンリーダーでもエラーの件数と内容がすぐ分かる。
 */
import { ref } from 'vue'
import NotificationBanner from './NotificationBanner.vue'

export interface ErrorItem {
  /** 移動先の入力欄の id */
  targetId: string
  label: string
  message: string
}

defineProps<{ items: ErrorItem[] }>()

const root = ref<HTMLElement | null>(null)

/** 項目へ移動する。ラジオボタンのグループは、選択中（なければ先頭）のボタンにフォーカスする */
function moveTo(targetId: string) {
  const el = document.getElementById(targetId)
  const target =
    el?.getAttribute('role') === 'radiogroup'
      ? el.querySelector<HTMLElement>('[role="radio"][aria-checked="true"], [role="radio"]')
      : el
  target?.scrollIntoView({ block: 'center' })
  target?.focus({ preventScroll: true })
}

// defineExpose = 親から ref 経由で呼べる関数を公開する（React の useImperativeHandle に相当）
defineExpose({
  focus() {
    root.value?.scrollIntoView({ block: 'start' })
    root.value?.focus({ preventScroll: true })
  },
})
</script>

<template>
  <div ref="root" class="error-summary" tabindex="-1">
    <NotificationBanner type="error" :title="`入力内容にエラーが${items.length}件あります`">
      <ul class="error-summary__list">
        <li v-for="item in items" :key="item.targetId">
          <a :href="`#${item.targetId}`" class="link" @click.prevent="moveTo(item.targetId)">
            {{ item.label }}：{{ item.message }}
          </a>
        </li>
      </ul>
    </NotificationBanner>
  </div>
</template>
