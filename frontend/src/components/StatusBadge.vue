<script setup lang="ts">
import { computed } from 'vue'
import type { ApplicationStatus } from '@/types'

const props = defineProps<{ status: ApplicationStatus; label: string }>()

const tone = computed(() => {
  switch (props.status) {
    case 'VERIFIED':
      return 'success'
    case 'NEEDS_REVIEW':
      return 'warning'
    case 'REJECTED':
    case 'EKYC_FAILED':
      return 'danger'
    default:
      return 'neutral'
  }
})
</script>

<template>
  <span class="badge" :class="`badge-${tone}`">{{ label }}</span>
</template>
