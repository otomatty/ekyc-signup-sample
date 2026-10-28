<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const steps = ['お申込み', '本人確認', '結果']
const current = computed(() => route.meta.step ?? 1)
</script>

<template>
  <header class="app-header">
    <div class="container">
      <span class="brand">サンプル通信 Web申込</span>
      <span class="tag">学習用サンプル</span>
    </div>
  </header>

  <main class="container">
    <ol class="stepper" aria-label="手続きの進み具合">
      <li
        v-for="(label, i) in steps"
        :key="label"
        :class="{ done: i + 1 < current, active: i + 1 === current }"
        :aria-current="i + 1 === current ? 'step' : undefined"
      >
        <span class="num">{{ i + 1 }}</span>{{ label }}
      </li>
    </ol>

    <!-- 現在のルートに対応するページがここに表示される -->
    <RouterView />
  </main>

  <footer class="container footer">
    このサイトは学習用のサンプルです。本人確認はモックで、実際の個人情報は扱いません。
  </footer>
</template>
