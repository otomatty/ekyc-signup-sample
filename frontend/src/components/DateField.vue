<script setup lang="ts">
/**
 * 生年月日の入力欄。
 * DADS の「日付ピッカー」にならい、年・月・日を別々の欄で入力してもらう。
 * 生年月日のように遠い過去の日付は、カレンダーから選ぶより直接入力のほうが速いため、カレンダーは付けない。
 *
 * Base UI の構成:
 *   FieldRoot（生年月日全体。サポートテキストとエラーを持つ）
 *     └ FieldsetRoot ＋ FieldsetLegend（3つの欄をグループにし、「生年月日」と読み上げる）
 *         └ FieldRoot × 3（年・月・日。それぞれに label を付ける）
 * 内側の欄にも、外側の FieldRoot のサポートテキストとエラーが aria-describedby で紐づく。
 */
import { FieldDescription, FieldError, FieldLabel, FieldRoot, FieldsetLegend, FieldsetRoot, Input } from 'base-ui-vue'
import { reactive, watch } from 'vue'
import { joinDateParts, splitDate, type DateParts } from '@/validators'
import RequirementBadge from './RequirementBadge.vue'

/** 'YYYY-MM-DD'。未入力は '' */
const model = defineModel<string>({ required: true })

defineProps<{
  name: string
  label: string
  required?: boolean
  error?: string
  hint?: string
}>()

const PARTS = [
  { key: 'year', unit: '年', maxlength: 4, autocomplete: 'bday-year' },
  { key: 'month', unit: '月', maxlength: 2, autocomplete: 'bday-month' },
  { key: 'day', unit: '日', maxlength: 2, autocomplete: 'bday-day' },
] as const

// 入力途中の値（'19' や全角数字など）をそのまま表示するため、欄ごとの値はこのコンポーネントで持つ
const parts = reactive<DateParts>(splitDate(model.value))

// サンプル入力などで親から値が変わったときだけ、欄の表示を合わせる
watch(model, (value) => {
  if (value !== joinDateParts(parts)) Object.assign(parts, splitDate(value))
})

function update(key: keyof DateParts, value: string) {
  parts[key] = value
  model.value = joinDateParts(parts)
}
</script>

<template>
  <FieldRoot :name="name" :invalid="!!error" class="field">
    <FieldsetRoot class="fieldset">
      <FieldsetLegend class="field__label">
        {{ label }}<RequirementBadge :optional="!required" />
      </FieldsetLegend>
      <FieldDescription v-if="hint" class="field__hint">{{ hint }}</FieldDescription>

      <div class="date-inputs">
        <FieldRoot v-for="p in PARTS" :key="p.key" :invalid="!!error" class="date-inputs__part">
          <Input
            :id="`field-${name}-${p.key}`"
            :value="parts[p.key]"
            type="text"
            inputmode="numeric"
            :maxlength="p.maxlength"
            :autocomplete="p.autocomplete"
            :aria-required="required || undefined"
            class="input"
            :class="`input--${p.key}`"
            @value-change="(value: string) => update(p.key, value)"
          />
          <FieldLabel class="date-inputs__unit">{{ p.unit }}</FieldLabel>
        </FieldRoot>
      </div>
    </FieldsetRoot>

    <FieldError v-if="error" match class="field__error">{{ error }}</FieldError>
  </FieldRoot>
</template>
