import { createRouter, createWebHistory } from 'vue-router'
import ApplyPage from './pages/ApplyPage.vue'
import { useApplicationStore } from './stores/application'

declare module 'vue-router' {
  interface RouteMeta {
    step?: number
    requiresSession?: boolean
  }
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'apply', component: ApplyPage, meta: { step: 1 } },
    {
      path: '/ekyc',
      name: 'ekyc',
      // 遅延読み込み（React.lazy に相当）
      component: () => import('./pages/EkycPage.vue'),
      meta: { step: 2, requiresSession: true },
    },
    {
      path: '/result',
      name: 'result',
      component: () => import('./pages/ResultPage.vue'),
      meta: { step: 3, requiresSession: true },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

// 申込前に本人確認や結果の画面を開かれたら、申込画面に戻す
router.beforeEach((to) => {
  if (to.meta.requiresSession && !useApplicationStore().hasSession) {
    return { name: 'apply' }
  }
})
