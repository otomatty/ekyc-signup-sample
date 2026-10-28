<script setup lang="ts">
import { computed } from 'vue'

// defineModel = 親の v-model を受け取る。React でいう value と onChange をまとめて受け取るイメージ
const model = defineModel<string>({ required: true })

// defineProps = props の型定義。React の props と同じく親から子への値渡し
const props = defineProps<{
  name: string
  label: string
  type?: string
  required?: boolean
  error?: string
  hint?: string
  autocomplete?: string
  placeholder?: string
  options?: { value: string; label: string }[]
  emptyOptionLabel?: string
}>()

const id = computed(() => `field-${props.name}`)
const describedBy = computed(() => (props.error ? `${id.value}-error` : props.hint ? `${id.value}-hint` : undefined))
</script>

<template>
  <div class="field" :class="{ 'has-error': error }">
    <label :for="id">
      {{ label }}
      <span v-if="required" class="req">必須</span>
    </label>

    <!-- v-if / v-else は条件付き描画。React の三項演算子に相当 -->
    <select
      v-if="options"
      :id="id"
      v-model="model"
      :name="name"
      :aria-invalid="!!error"
      :aria-describedby="describedBy"
    >
      <option value="">{{ emptyOptionLabel ?? '選択してください' }}</option>
      <!-- v-for は配列の繰り返し。React の map と同じく key を付ける -->
      <option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
    </select>
    <input
      v-else
      :id="id"
      v-model="model"
      :name="name"
      :type="type ?? 'text'"
      :autocomplete="autocomplete"
      :placeholder="placeholder"
      :aria-invalid="!!error"
      :aria-describedby="describedBy"
    />

    <p v-if="error" :id="`${id}-error`" class="field-error" role="alert">{{ error }}</p>
    <p v-else-if="hint" :id="`${id}-hint`" class="field-hint">{{ hint }}</p>
  </div>
</template>
