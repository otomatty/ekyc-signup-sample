<script setup lang="ts">
/**
 * ラジオボタンの選択欄。
 * 選択肢が少ない項目（性別、料金プラン）は、セレクトボックスより、
 * すべての選択肢が一度に見えて1回で選べるラジオボタンのほうが分かりやすい。
 *
 * Base UI の構成（Base UI のドキュメントにある組み方）:
 *   FieldRoot
 *     └ FieldsetRoot（as で RadioGroup として描画。role="radiogroup" になり、凡例で読み上げられる）
 *         ├ FieldsetLegend
 *         └ FieldItem ＋ FieldLabel ＋ RadioRoot（選択肢ごと）
 * 矢印キーでの選択の移動も Base UI が受け持つ。
 */
import {
  FieldDescription,
  FieldError,
  FieldItem,
  FieldLabel,
  FieldRoot,
  FieldsetLegend,
  FieldsetRoot,
  RadioGroup,
  RadioIndicator,
  RadioRoot,
} from 'base-ui-vue'
import RequirementBadge from './RequirementBadge.vue'

export interface RadioOption {
  value: string
  label: string
  /** 選択肢の補足（データ量など） */
  description?: string
}

const model = defineModel<string>({ required: true })

defineProps<{
  name: string
  label: string
  options: RadioOption[]
  required?: boolean
  error?: string
  hint?: string
  /** list: 縦に並べる / tile: 枠で囲んだカード型（料金プランなど、補足のある選択肢向け） */
  variant?: 'list' | 'tile'
}>()
</script>

<template>
  <FieldRoot :name="name" :invalid="!!error" class="field">
    <FieldsetRoot
      :id="`field-${name}`"
      :as="RadioGroup"
      :value="model"
      class="fieldset radio-group"
      :class="`radio-group--${variant ?? 'list'}`"
      @value-change="(value: unknown) => (model = String(value))"
    >
      <FieldsetLegend class="field__label">
        {{ label }}<RequirementBadge :optional="!required" />
      </FieldsetLegend>
      <FieldDescription v-if="hint" class="field__hint">{{ hint }}</FieldDescription>

      <div class="radio-group__options">
        <!-- v-for は配列の繰り返し。React の map と同じく key を付ける -->
        <FieldItem v-for="o in options" :key="o.value" class="radio-option">
          <FieldLabel class="radio-option__label">
            <RadioRoot :value="o.value" class="radio">
              <RadioIndicator class="radio__dot" />
            </RadioRoot>
            <span class="radio-option__text">
              <span class="radio-option__title">{{ o.label }}</span>
              <span v-if="o.description" class="radio-option__description">{{ o.description }}</span>
            </span>
          </FieldLabel>
        </FieldItem>
      </div>
    </FieldsetRoot>

    <FieldError v-if="error" match class="field__error">{{ error }}</FieldError>
  </FieldRoot>
</template>
