import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const aggregator = process.env.VITE_API_URL || 'http://localhost:8081'
const usersApi = process.env.VITE_USERS_API_URL || 'http://localhost:8082'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api/v1/auth': {
        target: usersApi,
        changeOrigin: true
      },
      '/api/v1/users': {
        target: usersApi,
        changeOrigin: true
      },
      '/api': {
        target: aggregator,
        changeOrigin: true
      }
    }
  }
})

