<script setup lang="ts">
/**
 * 要否ラベル。DADS では項目ラベルの横に「※必須」または「任意」を置く。
 * 必須は赤、任意は本文と同じ色にして、色だけに頼らず文字でも区別できるようにしている。
 */
defineProps<{ optional?: boolean }>()
</script>

<template>
  <span class="requirement" :class="{ 'requirement--optional': optional }">{{ optional ? '任意' : '※必須' }}</span>
</template>
