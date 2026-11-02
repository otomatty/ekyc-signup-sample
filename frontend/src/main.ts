import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
// デジタル庁デザインシステム（DADS）のデザイントークン（色、文字サイズ、角丸などの CSS 変数）
import '@digital-go-jp/design-tokens/dist/tokens.css'
import './style.css'

// React の <Provider> で包むのに近い。Pinia を先に入れ、ルーターのガードからストアを使えるようにする
createApp(App).use(createPinia()).use(router).mount('#app')
