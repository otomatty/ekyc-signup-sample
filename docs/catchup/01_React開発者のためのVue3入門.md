# React 開発者のための Vue 3 入門

このリポジトリの `frontend/` は Vue 3（Composition API、`<script setup>`）で書いています。React の知識を前提に、違いだけを説明します。

---

## 1. いちばん大きな違い

| | React | Vue 3 |
|---|---|---|
| コンポーネントの実行 | 状態が変わるたびに関数全体を実行し直す | `<script setup>` は最初に **1回だけ** 実行する |
| 変更の検知 | `setState` を呼んだら再レンダー | 値の読み書きを Vue が追跡し、変わった部分だけ更新 |
| 依存の指定 | `useMemo`、`useEffect` の依存配列 | 不要（自動で追跡） |
| 値の更新 | イミュータブルに作り直す | そのまま書き換えてよい |

この違いから、React でよく気にする「古い値を参照してしまう（stale closure）」「`useCallback` で関数を固定する」といった問題は、Vue ではほぼ起きません。代わりに、Vue 特有の注意点（4章）があります。

---

## 2. 対応表

| やりたいこと | React | Vue 3 | このリポジトリの例 |
|---|---|---|---|
| 状態 | `useState` | `ref()`、`reactive()` | `stores/application.ts`、`pages/ApplyPage.vue` |
| 派生値 | `useMemo` | `computed()` | `ApplyPage.vue` の `errors` |
| 副作用 | `useEffect` | `watch()`、`watchEffect()` | − |
| マウント時 | `useEffect(() => {}, [])` | `onMounted()` | `ResultPage.vue` |
| 後片付け | `useEffect` の戻り値 | `onUnmounted()`、`onScopeDispose()` | `composables/usePolling.ts` |
| 画面の記述 | JSX | テンプレート | 各 `.vue` |
| 条件 | `{cond && <A/>}`、三項演算子 | `v-if`、`v-else-if`、`v-else` | `FormField.vue` |
| 繰り返し | `items.map(i => <li key=...>)` | `v-for="i in items" :key="..."` | `FormField.vue` |
| 属性の値を式に | `value={x}` | `:value="x"`（`v-bind` の省略形） | 各所 |
| イベント | `onClick={fn}` | `@click="fn"`（`v-on` の省略形） | 各所 |
| フォーム入力 | `value` ＋ `onChange` | `v-model` | `ApplyPage.vue` |
| props | 関数の引数 | `defineProps()` | `FormField.vue` |
| 親への通知 | コールバックを props で渡す | `defineEmits()` で `emit` | − |
| 子コンポーネントの v-model | `value` ＋ `onChange` を自作 | `defineModel()` | `FormField.vue` |
| 子要素の差し込み | `children` | `<slot>` | − |
| ロジックの再利用 | カスタムフック | composable | `usePolling.ts` |
| グローバル状態 | Context、Zustand、Redux | Pinia | `stores/application.ts` |
| ルーティング | React Router | Vue Router | `router.ts` |
| 遅延読み込み | `React.lazy` | `() => import('./X.vue')` | `router.ts` |

---

## 3. コードで比べる

### 3.1 状態と派生値

```tsx
// React
const [name, setName] = useState('')
const isValid = useMemo(() => name.trim().length > 0, [name])
```

```ts
// Vue
const name = ref('')
const isValid = computed(() => name.value.trim().length > 0) // 依存は自動
```

### 3.2 フォーム入力

```tsx
// React
<input value={name} onChange={(e) => setName(e.target.value)} />
```

```vue
<!-- Vue -->
<input v-model="name" />
```

### 3.3 オブジェクトの状態

```tsx
// React: 作り直す
setForm({ ...form, name: 'x' })
```

```ts
// Vue: reactive ならそのまま書き換える
const form = reactive({ name: '', email: '' })
form.name = 'x'
```

`ApplyPage.vue` の `fillSample` は `Object.assign(form, sample.form)` で一括で書き換えています。

### 3.4 自作コンポーネントで v-model を受ける

```vue
<!-- 子: FormField.vue -->
<script setup lang="ts">
const model = defineModel<string>({ required: true })
defineProps<{ label: string }>()
</script>
<template>
  <label>{{ label }} <input v-model="model" /></label>
</template>

<!-- 親 -->
<FormField v-model="form.name" label="氏名" />
```

React なら `value` と `onChange` の2つの props を作るところを、`defineModel` 1つで済ませています。

### 3.5 親へのイベント通知（emit）

このリポジトリでは使っていませんが、よく出てくる形です。

```vue
<script setup lang="ts">
const emit = defineEmits<{ (e: 'retry'): void; (e: 'select', id: string): void }>()
</script>
<template>
  <button @click="emit('retry')">再試行</button>
</template>

<!-- 親 -->
<ResultCard @retry="onRetry" @select="(id) => open(id)" />
```

### 3.6 カスタムフックと composable

```ts
// Vue の composable（usePolling.ts を簡略化）
export function usePolling<T>(fetcher: () => Promise<T>) {
  const data = shallowRef<T | null>(null)
  let timer: ReturnType<typeof setTimeout> | undefined
  async function tick() {
    data.value = await fetcher()
    timer = setTimeout(tick, 2000)
  }
  function start() { void tick() }
  onScopeDispose(() => clearTimeout(timer)) // コンポーネント破棄時に止める
  return { data, start }
}
```

React のフックとの違い:

- 呼ばれるのは setup の中で1回だけ。毎回の再実行はない
- 「条件分岐の中で呼ばない」などのルールは、setup の中で同期的に呼ぶことだけ守ればよい
- 返した `ref` は呼び出し側でそのままリアクティブに使える

### 3.7 グローバル状態（Pinia）

```ts
// stores/application.ts（Setup Store 形式）
export const useApplicationStore = defineStore('application', () => {
  const applicationId = ref<string | null>(null)
  const hasSession = computed(() => applicationId.value !== null)
  function setSession(id: string) { applicationId.value = id }
  return { applicationId, hasSession, setSession }
})

// 使う側
const store = useApplicationStore()
store.setSession('abc')
console.log(store.hasSession) // ストア経由では .value は不要
```

---

## 4. React 経験者がつまずくところ

### 4.1 `.value` の付け忘れ

| 場所 | `ref` の値の読み方 |
|---|---|
| `<script setup>` の中 | `name.value` |
| テンプレートの中 | `name`（自動で取り出される） |
| Pinia ストアのプロパティ | `store.applicationId`（自動で取り出される） |

### 4.2 分割代入でリアクティブでなくなる

```ts
const store = useApplicationStore()
const { applicationId } = store            // NG: ただの値になり、更新が反映されない
const { applicationId } = storeToRefs(store) // OK

const form = reactive({ name: '' })
const { name } = form          // NG
const { name } = toRefs(form)  // OK
```

### 4.3 `ref` と `reactive` の使い分け

迷ったら `ref` を使います。`reactive` はオブジェクト専用で、変数ごと置き換えると追跡が切れます（`form = {...}` は NG、`Object.assign(form, {...})` は OK）。このリポジトリでは、フォーム全体だけ `reactive`、ほかは `ref` にしています。

### 4.4 `watch` と `watchEffect`

| | 動く条件 | 用途 |
|---|---|---|
| `watch(source, cb)` | 指定した値が変わったとき | 変化前後の値が欲しい、特定の値だけ見たい |
| `watchEffect(cb)` | 中で読んだ値のどれかが変わったとき（最初にも1回実行） | 依存を書かずに済ませたい |

派生値は `computed` で済むことが多く、`watch` はそれほど使いません。React で `useEffect` に書いていた「state から state を作る」処理は、Vue では `computed` にします。

### 4.5 ページごとの移動で状態が消える

本人確認ではベンダーの画面へページごと移動するため、戻ってきたときに Pinia の状態は消えています。このリポジトリでは sessionStorage に保存して復元しています（`stores/application.ts`）。これは React でも同じ問題です。

---

## 5. 既存コードが Options API だった場合

古い Vue のコードは、Options API という書き方のことがあります。読めれば十分です。

```js
export default {
  props: { label: String },
  data() {                 // 状態（ref / reactive に相当）
    return { name: '' }
  },
  computed: {              // 派生値（computed に相当）
    isValid() { return this.name.length > 0 }
  },
  watch: {                 // watch に相当
    name(newVal, oldVal) {}
  },
  mounted() {},            // onMounted に相当
  methods: {               // 関数
    submit() { this.$emit('submit', this.name) }
  },
}
```

`this.name` のように `this` 経由で触るのが特徴です。既存のコードを引き継ぐときは、どちらで書かれているかを最初に確認しましょう。

---

## 6. 参考

- Vue 公式ガイド（日本語）: https://ja.vuejs.org/guide/introduction
- Pinia: https://pinia.vuejs.org/
- Vue Router: https://router.vuejs.org/
