<script setup lang="ts">
/**
 * テキストの入力欄。
 * - 見た目: デジタル庁デザインシステム（DADS）の「インプットテキスト」に合わせる
 *   （項目ラベル → 要否ラベル → サポートテキスト → 入力欄 → エラーテキストの順）
 * - 仕組み: Base UI の Field に任せる。label の for、aria-describedby（サポートテキストとエラー）、
 *   aria-invalid を自動で付けてくれる
 */
import { FieldDescription, FieldError, FieldLabel, FieldRoot, Input } from 'base-ui-vue'
import RequirementBadge from './RequirementBadge.vue'

// defineModel = 親の v-model を受け取る。React でいう value と onChange をまとめて受け取るイメージ
const model = defineModel<string>({ required: true })

// defineProps = props の型定義。React の props と同じく親から子への値渡し
defineProps<{
  name: string
  label: string
  type?: 'text' | 'email' | 'tel'
  required?: boolean
  error?: string
  /** サポートテキスト。入力例もここに書く（DADS ではプレースホルダーに頼らない） */
  hint?: string
  autocomplete?: string
  inputmode?: 'text' | 'numeric' | 'tel' | 'email'
  maxlength?: number
  /** 入力欄の幅。入る文字数の目安に合わせる（郵便番号は短く、住所は長く） */
  width?: 'full' | 'medium' | 'short'
}>()
</script>

<template>
  <!-- invalid を渡すと、Base UI が data-invalid（見た目用）と aria-invalid（読み上げ用）を付ける -->
  <FieldRoot :name="name" :invalid="!!error" class="field">
    <FieldLabel class="field__label">
      {{ label }}<RequirementBadge :optional="!required" />
    </FieldLabel>

    <!-- v-if は条件付き描画。React の三項演算子や && に相当 -->
    <FieldDescription v-if="hint" class="field__hint">{{ hint }}</FieldDescription>

    <!-- Base UI の Input は v-model ではなく、value と value-change で値をやり取りする -->
    <Input
      :id="`field-${name}`"
      :value="model"
      :type="type ?? 'text'"
      :autocomplete="autocomplete"
      :inputmode="inputmode"
      :maxlength="maxlength"
      :aria-required="required || undefined"
      class="input"
      :class="`input--${width ?? 'full'}`"
      @value-change="(value: string) => (model = value)"
    />

    <!-- エラーは画面側（validators.ts）で決めるので、match で「常に表示」にして v-if で出し分ける -->
    <FieldError v-if="error" match class="field__error">{{ error }}</FieldError>
  </FieldRoot>
</template>
