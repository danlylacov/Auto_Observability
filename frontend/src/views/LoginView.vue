<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="title">Вход</h1>
      <form @submit.prevent="onSubmit">
        <label class="field">
          <span>Имя пользователя</span>
          <input v-model="username" type="text" class="input" autocomplete="username" required />
        </label>
        <label class="field">
          <span>Пароль</span>
          <input
            v-model="password"
            type="password"
            class="input"
            autocomplete="current-password"
            required
          />
        </label>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
          <span v-if="loading" class="loading"></span>
          <span v-else>Войти</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '../services/api'
import { setSession } from '../auth/session'

const route = useRoute()
const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    const data = await authApi.login(username.value.trim(), password.value)
    setSession(data.access_token, username.value.trim(), data.role)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/containers'
    await router.replace(redirect || '/containers')
  } catch (e: unknown) {
    error.value = 'Неверный логин или пароль'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: calc(100vh - 60px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 380px;
  padding: 28px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 10px;
}

.title {
  margin: 0 0 20px;
  font-size: 22px;
  font-weight: 600;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
  font-size: 14px;
  color: var(--text-secondary);
}

.error {
  color: #e74c3c;
  font-size: 14px;
  margin-bottom: 12px;
}

.btn-block {
  width: 100%;
  margin-top: 8px;
}
</style>
