import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { restoreSession } from './auth/session'
import './style.css'

async function bootstrap() {
  await restoreSession()
  const app = createApp(App)
  app.use(router)
  app.mount('#app')
}

bootstrap()

