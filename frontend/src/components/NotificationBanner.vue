<script setup lang="ts">
/**
 * お知らせ・エラーの帯。DADS の「ノティフィケーションバナー」に合わせ、
 * 色だけでなくアイコンとタイトルでも種類が分かるようにしている。
 */
export type BannerType = 'info' | 'success' | 'warning' | 'error'

defineProps<{ type: BannerType; title?: string }>()

// アイコンの形は DADS のバナーのものに合わせている
const ICONS: Record<BannerType, { label: string; paths: { d: string; fill: string }[] }> = {
  info: {
    label: 'お知らせ',
    paths: [
      { d: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Z', fill: 'currentColor' },
      { d: 'M11 11h2v6h-2zM11 7h2v2h-2z', fill: 'Canvas' },
    ],
  },
  success: {
    label: '成功',
    paths: [
      { d: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Z', fill: 'currentColor' },
      { d: 'm17.6 9.6-7 7-4.3-4.3L7.7 11l2.9 2.9 5.7-5.6 1.3 1.4Z', fill: 'Canvas' },
    ],
  },
  warning: {
    label: '警告',
    paths: [
      { d: 'M1 21 12 2l11 19H1Z', fill: 'currentColor' },
      { d: 'M13 15h-2v-5h2v5ZM13 18h-2v-2h2v2Z', fill: 'Canvas' },
    ],
  },
  error: {
    label: 'エラー',
    paths: [
      { d: 'M8.25 21 3 15.75v-7.5L8.25 3h7.5L21 8.25v7.5L15.75 21h-7.5Z', fill: 'currentColor' },
      {
        d: 'm12 13.4-2.85 2.85-1.4-1.4L10.6 12 7.75 9.15l1.4-1.4L12 10.6l2.85-2.85 1.4 1.4L13.4 12l2.85 2.85-1.4 1.4L12 13.4Z',
        fill: 'Canvas',
      },
    ],
  },
}
</script>

<template>
  <div class="banner" :class="`banner--${type}`">
    <svg class="banner__icon" viewBox="0 0 24 24" role="img" :aria-label="ICONS[type].label">
      <path v-for="p in ICONS[type].paths" :key="p.d" :d="p.d" :fill="p.fill" />
    </svg>
    <div class="banner__body">
      <p v-if="title" class="banner__title">{{ title }}</p>
      <slot />
    </div>
  </div>
</template>
