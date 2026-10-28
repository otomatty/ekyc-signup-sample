import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import './style.css'

// React の <Provider> で包むのに近い。Pinia を先に入れ、ルーターのガードからストアを使えるようにする
createApp(App).use(createPinia()).use(router).mount('#app')
