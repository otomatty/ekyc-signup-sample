import { onScopeDispose, ref, shallowRef } from 'vue'
import { ApiError } from '@/api/client'

export interface PollingOptions<T> {
  /** 取得した値を見て、ポーリングを終えてよいか判定する */
  isDone: (value: T) => boolean
  intervalMs?: number
  maxAttempts?: number
}

/**
 * 一定間隔で値を取りに行く composable。
 * React のカスタムフック（useXxx）に相当するが、依存配列やルールズ・オブ・フックスはない。
 * setup の中で1回呼ばれ、その後は ref の変化で画面が更新される。
 */
export function usePolling<T>(fetcher: () => Promise<T>, options: PollingOptions<T>) {
  const { isDone, intervalMs = 2000, maxAttempts = 60 } = options

  const data = shallowRef<T | null>(null)
  const error = ref<Error | null>(null)
  const isPolling = ref(false)
  const timedOut = ref(false)

  let timer: ReturnType<typeof setTimeout> | undefined
  let attempts = 0

  async function tick() {
    attempts += 1
    try {
      const value = await fetcher()
      data.value = value
      error.value = null
      if (isDone(value)) {
        stop()
        return
      }
    } catch (e) {
      error.value = e instanceof Error ? e : new Error(String(e))
      // 認証切れ・見つからないは、待っても直らないので止める
      if (e instanceof ApiError && (e.status === 401 || e.status === 404)) {
        stop()
        return
      }
    }
    if (!isPolling.value) return
    if (attempts >= maxAttempts) {
      timedOut.value = true
      stop()
      return
    }
    timer = setTimeout(tick, intervalMs)
  }

  function start() {
    stop()
    attempts = 0
    timedOut.value = false
    isPolling.value = true
    void tick()
  }

  function stop() {
    isPolling.value = false
    if (timer) clearTimeout(timer)
    timer = undefined
  }

  // コンポーネントが破棄されたら止める（useEffect のクリーンアップ関数に相当）
  onScopeDispose(stop)

  return { data, error, isPolling, timedOut, start, stop }
}
