
import { createApp } from 'vue'
import App from './App.vue'
import router from './router' // S.7 路由
import { createPinia } from 'pinia' // S.8 状态管理
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/dark-theme.css'

const app = createApp(App)
app.use(router)
app.use(createPinia())
app.use(ElementPlus)
app.mount('#app')


