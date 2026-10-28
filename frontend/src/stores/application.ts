import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

/**
 * 申込ID と受け渡しトークンを持つストア（Setup Store 形式）。
 *
 * 注意: 本人確認ではベンダーの画面へページごと移動するため、戻ってきた時点で
 * Pinia の状態（メモリ上の値）は消えている。そこで sessionStorage にも保存する。
 * sessionStorage はタブを閉じると消えるので、長く残したくない値に向いている。
 */
const STORAGE_KEY = 'ekyc-sample:session'

interface SavedSession {
  applicationId: string
  handoffToken: string
}

function load(): SavedSession | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as SavedSession) : null
  } catch {
    return null
  }
}

export const useApplicationStore = defineStore('application', () => {
  const saved = load()
  // ref = React の useState に相当。ただし setter はなく、.value に代入する
  const applicationId = ref<string | null>(saved?.applicationId ?? null)
  const handoffToken = ref<string | null>(saved?.handoffToken ?? null)

  // computed = useMemo に相当。依存（applicationId, handoffToken）は自動で追跡される
  const hasSession = computed(() => applicationId.value !== null && handoffToken.value !== null)

  function setSession(id: string, token: string) {
    applicationId.value = id
    handoffToken.value = token
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ applicationId: id, handoffToken: token }))
    } catch {
      // プライベートモードなどで保存できない場合は、メモリ上の値だけで続ける
    }
  }

  function clear() {
    applicationId.value = null
    handoffToken.value = null
    try {
      sessionStorage.removeItem(STORAGE_KEY)
    } catch {
      // 何もしない
    }
  }

  return { applicationId, handoffToken, hasSession, setSession, clear }
})
